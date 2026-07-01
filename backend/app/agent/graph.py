from langgraph.graph import StateGraph, END

from app.agent.nodes import (
    AgentState,
    node_trigger_scrape,
    node_await_scrape,
    node_analyze_tech,
    node_analyze_hiring,
    node_analyze_product,
    node_synthesize,
)
from app.utils.logger import get_logger

log = get_logger(__name__)


def _route_after_await(state: AgentState) -> str:
    """
    Conditional edge after await_scrape.
    If scrape is done → proceed to analysis.
    If not → loop back to keep waiting.
    """
    if state.get("scrape_done"):
        return "analyze_tech"
    return "await_scrape"


def _build_graph():
    graph = StateGraph(AgentState)

    # Add all nodes
    graph.add_node("trigger_scrape",   node_trigger_scrape)
    graph.add_node("await_scrape",     node_await_scrape)
    graph.add_node("analyze_tech",     node_analyze_tech)
    graph.add_node("analyze_hiring",   node_analyze_hiring)
    graph.add_node("analyze_product",  node_analyze_product)
    graph.add_node("synthesize",       node_synthesize)

    # Entry point
    graph.set_entry_point("trigger_scrape")

    # Linear edges
    graph.add_edge("trigger_scrape", "await_scrape")

    # Conditional: keep polling OR move to analysis
    graph.add_conditional_edges(
        "await_scrape",
        _route_after_await,
        {
            "await_scrape": "await_scrape",
            "analyze_tech": "analyze_tech",
        },
    )

    # Analysis chain — sequential so each builds on previous
    graph.add_edge("analyze_tech",    "analyze_hiring")
    graph.add_edge("analyze_hiring",  "analyze_product")
    graph.add_edge("analyze_product", "synthesize")
    graph.add_edge("synthesize",      END)

    return graph.compile()


# Compiled graph — singleton, import this
agent_graph = _build_graph()


async def run_agent(company: str, job_id: str) -> None:
    """
    Run the full WatchR agent pipeline.
    Called as FastAPI background task.
    Updates MongoDB report document as it progresses.
    """
    from datetime import datetime
    from app.database import get_db
    from app.models.schemas import JobStatus
    import asyncio

    db = get_db()

    initial_state: AgentState = {
        "company":           company,
        "job_id":            job_id,
        "scrape_task_id":    "",
        "scrape_done":       False,
        "articles_scraped":  0,
        "github_data":       {},
        "sources_used":      [],
        "tech_signals":      [],
        "hiring_signals":    [],
        "product_signals":   [],
        "ai_maturity_score": 0.0,
        "ai_maturity_notes": "",
        "executive_summary": "",
        "step_log":          [],
        "error":             "",
    }

    # Mark as running
    await db.reports.update_one(
        {"job_id": job_id},
        {"$set": {"status": JobStatus.RUNNING}},
    )

    try:
        # LangGraph is synchronous — run in thread to avoid blocking event loop
        final_state = await asyncio.to_thread(agent_graph.invoke, initial_state)

        # Persist final results
        await db.reports.update_one(
            {"job_id": job_id},
            {"$set": {
                "status":            JobStatus.DONE,
                "tech_signals":      final_state.get("tech_signals", []),
                "hiring_signals":    final_state.get("hiring_signals", []),
                "product_signals":   final_state.get("product_signals", []),
                "ai_maturity_score": final_state.get("ai_maturity_score", 0.0),
                "ai_maturity_notes": final_state.get("ai_maturity_notes", ""),
                "executive_summary": final_state.get("executive_summary", ""),
                "sources_used":      final_state.get("sources_used", []),
                "articles_scraped":  final_state.get("articles_scraped", 0),
                "completed_at":      datetime.utcnow(),
                "error":             final_state.get("error", ""),
            }},
        )

        # Update company metadata
        await db.companies.update_one(
            {"name": company},
            {
                "$set": {
                    "last_scraped": datetime.utcnow(),
                    "status":       JobStatus.DONE,
                },
                "$inc": {"report_count": 1},
            },
        )

        log.info("Agent complete for %s [job: %s]", company, job_id[:8])

    except Exception as e:
        log.error("Agent failed for %s: %s", company, e)
        await db.reports.update_one(
            {"job_id": job_id},
            {"$set": {
                "status": JobStatus.FAILED,
                "error":  str(e),
            }},
        )
        await db.companies.update_one(
            {"name": company},
            {"$set": {"status": JobStatus.FAILED}},
        )
        raise
