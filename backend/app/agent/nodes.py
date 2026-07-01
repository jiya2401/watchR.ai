# Each function = one LangGraph node.
# State flows: trigger → await → analyze_tech → analyze_hiring → analyze_product → synthesize

import json
import asyncio
import time
from typing import TypedDict, Any

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.rag.retriever import retrieve, retrieve_multi
from app.models.schemas import TechSignal, HiringSignal, ProductSignal, StepLog
from app.agent.prompts import (
    tech_stack_prompt, hiring_prompt,
    product_prompt, synthesis_prompt,
)
from app.utils.logger import get_logger

log = get_logger(__name__)
settings = get_settings()
genai.configure(api_key=settings.gemini_api_key)

fast_llm  = genai.GenerativeModel(settings.gemini_fast_model)
smart_llm = genai.GenerativeModel(settings.gemini_smart_model)


# Agent State 
# This TypedDict flows through every node in the graph.
# Each node receives it, modifies it, returns it.

class AgentState(TypedDict):
    company:            str
    job_id:             str
    # Scrape tracking
    scrape_task_id:     str
    scrape_done:        bool
    articles_scraped:   int
    github_data:        dict[str, Any]
    sources_used:       list[str]
    # Analysis results
    tech_signals:       list[dict]
    hiring_signals:     list[dict]
    product_signals:    list[dict]
    ai_maturity_score:  float
    ai_maturity_notes:  str
    executive_summary:  str
    # Progress tracking
    step_log:           list[dict]
    error:              str


# Helpers

def _log(state: AgentState, step: str, message: str, preview: str = "") -> AgentState:
    # Append a step log entry. Also persists to MongoDB for WebSocket streaming.
    entry = StepLog(step=step, message=message, preview=preview)
    state["step_log"].append(entry.model_dump(mode="json"))
    log.info("[%s] %s | %s → %s", state["company"], step, message[:80], preview[:40])

    # Persist to MongoDB so WebSocket can poll and stream
    try:
        from pymongo import MongoClient
        from app.config import get_settings
        s = get_settings()
        client = MongoClient(s.mongo_uri, serverSelectionTimeoutMS=2000)
        db = client[s.mongo_db]
        db.reports.update_one(
            {"job_id": state["job_id"]},
            {"$push": {"step_log": entry.model_dump(mode="json")}},
        )
        client.close()
    except Exception as e:
        log.warning("Step log persist failed: %s", e)

    return state


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=5, max=30))
def _call_fast(prompt: str) -> str:
    time.sleep(6)  # ~10 RPM free tier → 1 call per 6s
    r = fast_llm.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.3,  # low temp = consistent structured output
            max_output_tokens=2048,
        ),
    )
    return r.text


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=30, max=90))
def _call_smart(prompt: str) -> str:
    time.sleep(35)  # 2 RPM free tier
    r = smart_llm.generate_content(
        prompt,
        generation_config=genai.types.GenerationConfig(
            temperature=0.5,
            max_output_tokens=4096,
        ),
    )
    return r.text


def _parse_json(text: str) -> list | dict:
    # Extract JSON from LLM response, stripping markdown fences.
    text = text.strip()
    if "```" in text:
        lines = text.split("\n")
        # Find first { or [ after ```
        in_block = False
        clean_lines = []
        for line in lines:
            if line.startswith("```"):
                in_block = not in_block
                continue
            if in_block or not line.startswith("```"):
                clean_lines.append(line)
        text = "\n".join(clean_lines).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Try to find JSON substring
        import re
        match = re.search(r"[\[\{].*[\]\}]", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        log.warning("JSON parse failed. Raw: %s...", text[:100])
        return []


def _format_chunks(chunks: list[dict]) -> str:
    # Format retrieved chunks for LLM context.
    if not chunks:
        return "No relevant content found in knowledge base."
    parts = []
    for i, c in enumerate(chunks, 1):
        parts.append(
            f"[{i}] Source: {c['source']} | {c['title'][:60]} | Relevance: {c['score']}\n"
            f"{c['text']}\n"
        )
    return "\n---\n".join(parts)


# Node 1: Trigger Scrape

def node_trigger_scrape(state: AgentState) -> AgentState:
    # Kick off Celery scraping task.
    from app.celery_tasks.scraping_tasks import run_full_scrape

    company = state["company"]
    state = _log(state, "trigger_scrape",
                 f"Launching scrapers for {company}...",
                 "Blog crawler + GitHub API")

    try:
        task = run_full_scrape.delay(company, state["job_id"])
        state["scrape_task_id"] = task.id
        state = _log(state, "trigger_scrape",
                     "Scrapers running in background",
                     f"Task ID: {task.id[:8]}...")
    except Exception as e:
        log.error("Failed to trigger scrape: %s", e)
        state["scrape_done"] = True  # proceed without data
        state["error"] = str(e)

    return state


# Node 2: Await Scrape

def node_await_scrape(state: AgentState) -> AgentState:
    from celery.result import AsyncResult

    task_id = state.get("scrape_task_id", "")
    if not task_id:
        state["scrape_done"] = True
        return state

    state = _log(state, "await_scrape",
                 "Collecting data from blog and GitHub...",
                 "Checking every 20 seconds")

    max_attempts = 24  # 24 × 20s = 8 minutes
    for attempt in range(max_attempts):
        try:
            result = AsyncResult(task_id)
            if result.ready():
                if result.successful():
                    data = result.result or {}
                    state["articles_scraped"] = data.get("blog_count", 0)
                    state["github_data"] = data.get("github", {})
                    state["sources_used"] = data.get("sources", [])
                    state = _log(
                        state, "await_scrape",
                        f"Data collected: {state['articles_scraped']} blog articles",
                        f"GitHub: {state['github_data'].get('repo_count', 0)} repos | "
                        f"Languages: {list(state['github_data'].get('languages', {}).keys())[:3]}",
                    )
                else:
                    state = _log(state, "await_scrape",
                                 "Scraping had errors — proceeding with available data",
                                 str(result.result)[:80])
                state["scrape_done"] = True
                return state

            # Log progress every 2 attempts
            if attempt % 2 == 0:
                state = _log(state, "await_scrape",
                             f"Still collecting... ({attempt * 20}s elapsed)",
                             "Playwright is reading blog articles")

            time.sleep(20)

        except Exception as e:
            log.warning("Polling error: %s", e)
            time.sleep(10)

    # Timeout — proceed with whatever was collected
    state["scrape_done"] = True
    state = _log(state, "await_scrape",
                 "Timeout — proceeding with available data",
                 "Some sources may be incomplete")
    return state


# Node 3: Analyze Tech Stack

def node_analyze_tech(state: AgentState) -> AgentState:
    company = state["company"]
    state = _log(state, "analyze_tech",
                 f"Analyzing {company}'s technology choices...",
                 "Searching for stack signals")

    chunks = retrieve_multi(company, [
        "technology infrastructure programming languages frameworks",
        "system architecture microservices distributed systems",
        "database storage cloud platform deployment",
        "machine learning AI tools pipeline",
    ], k_per_query=5)

    if not chunks:
        state = _log(state, "analyze_tech", "No tech data found", "Skipping")
        state["tech_signals"] = []
        return state

    context = _format_chunks(chunks[:12])
    prompt = tech_stack_prompt(company, context)

    try:
        raw = _call_fast(prompt)
        parsed = _parse_json(raw)
        signals = []
        for item in (parsed if isinstance(parsed, list) else []):
            try:
                signals.append(TechSignal(**item).model_dump())
            except Exception:
                continue
        state["tech_signals"] = signals
        top = [s["technology"] for s in signals[:4]]
        state = _log(state, "analyze_tech",
                     f"Found {len(signals)} technology signals",
                     " · ".join(top))
    except Exception as e:
        log.error("Tech analysis failed: %s", e)
        state["tech_signals"] = []
        state = _log(state, "analyze_tech", "Tech analysis failed", str(e)[:60])

    return state


# Node 4: Analyze Hiring

def node_analyze_hiring(state: AgentState) -> AgentState:
    company = state["company"]
    state = _log(state, "analyze_hiring",
                 f"Decoding {company}'s hiring patterns...",
                 "What do open roles reveal?")

    chunks = retrieve_multi(company, [
        "hiring engineering team roles positions",
        "machine learning data science AI research",
        "platform infrastructure devops SRE",
        "product design growth",
    ], k_per_query=4)

    github = state.get("github_data", {})
    github_ctx = (
        f"GitHub topics: {github.get('topics', [])}\n"
        f"Primary languages: {list(github.get('languages', {}).keys())[:8]}\n"
        f"Recent repos: {[r.get('name') for r in github.get('repos', [])[:5]]}\n"
        f"Total stars: {github.get('total_stars', 0)}"
    )
    context = _format_chunks(chunks[:10])
    prompt = hiring_prompt(company, context, github_ctx)

    try:
        raw = _call_fast(prompt)
        parsed = _parse_json(raw)
        signals = []
        for item in (parsed if isinstance(parsed, list) else []):
            try:
                signals.append(HiringSignal(**item).model_dump())
            except Exception:
                continue
        state["hiring_signals"] = signals
        top = signals[0]["inferred_initiative"][:80] if signals else "No signals"
        state = _log(state, "analyze_hiring",
                     f"Found {len(signals)} hiring signals",
                     top)
    except Exception as e:
        log.error("Hiring analysis failed: %s", e)
        state["hiring_signals"] = []

    return state


# Node 5: Analyze Product

def node_analyze_product(state: AgentState) -> AgentState:
    company = state["company"]
    state = _log(state, "analyze_product",
                 f"Predicting {company}'s next product moves...",
                 "Connecting signals → predictions")

    chunks = retrieve_multi(company, [
        "product launch feature announcement new release",
        "roadmap future plans strategy growth",
        "customer user experience innovation",
        "revenue business model monetization",
    ], k_per_query=5)

    context = _format_chunks(chunks[:12])
    prompt = product_prompt(company, context, state.get("tech_signals", []))

    try:
        raw = _call_fast(prompt)
        parsed = _parse_json(raw)

        if isinstance(parsed, dict):
            signals = []
            for item in parsed.get("product_signals", []):
                try:
                    signals.append(ProductSignal(**item).model_dump())
                except Exception:
                    continue
            state["product_signals"] = signals

            ai = parsed.get("ai_maturity", {})
            state["ai_maturity_score"] = float(ai.get("score", 0.0))
            state["ai_maturity_notes"] = ai.get("notes", "")

            top = signals[0]["feature"] if signals else "No predictions"
            state = _log(
                state, "analyze_product",
                f"Predicted {len(signals)} product moves · AI maturity: {state['ai_maturity_score']}/10",
                top,
            )
        else:
            state["product_signals"] = []

    except Exception as e:
        log.error("Product analysis failed: %s", e)
        state["product_signals"] = []

    return state


# Node 6: Synthesize

def node_synthesize(state: AgentState) -> AgentState:
    company = state["company"]
    state = _log(state, "synthesize",
                 f"Writing WatchR intelligence report for {company}...",
                 "Using Gemini Pro for final synthesis")

    prompt = synthesis_prompt(
        company,
        state.get("tech_signals", []),
        state.get("hiring_signals", []),
        state.get("product_signals", []),
        state.get("ai_maturity_score", 0.0),
        state.get("ai_maturity_notes", ""),
    )

    try:
        summary = _call_smart(prompt)
        state["executive_summary"] = summary
        state = _log(
            state, "synthesize",
            "Intelligence report complete ✓",
            summary[:100] + "..." if len(summary) > 100 else summary,
        )
    except Exception as e:
        log.error("Synthesis failed: %s", e)
        state["executive_summary"] = "Report generation failed. Raw signals are available above."
        state["error"] = str(e)

    return state 
