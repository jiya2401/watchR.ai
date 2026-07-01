# All LLM prompts in one place.
# Tuning prompts = tuning signal quality. Change here, affects everything.

def tech_stack_prompt(company: str, context: str) -> str:
    return f"""You are a senior technology analyst at a top-tier VC firm analyzing {company}.

Study these content snippets from their engineering blog and GitHub:

{context}

Extract technology signals — what tools, frameworks, infrastructure choices are they making?

Return ONLY a valid JSON array. No markdown. No explanation. No preamble:
[
  {{
    "technology": "Apache Kafka",
    "evidence": "Two blog posts detail their migration to event-driven architecture using Kafka for real-time order processing",
    "confidence": 0.88,
    "signal_type": "adopting"
  }}
]

Rules:
- signal_type must be exactly one of: "adopting", "scaling", "retiring"
- confidence: 0.0 to 1.0 based on how strong the evidence is
- Only include technologies with ACTUAL evidence in the content
- Return 4 to 10 signals
- Be specific — "Kubernetes" not "container orchestration"
- Focus on signals that reveal strategic direction, not trivial choices"""


def hiring_prompt(company: str, context: str, github_context: str) -> str:
    return f"""You are a talent intelligence analyst studying {company}'s hiring patterns.

CONTENT FROM THEIR BLOG AND JOB POSTINGS:
{context}

GITHUB DATA:
{github_context}

What do their hiring patterns reveal about their upcoming product and technical initiatives?

Return ONLY a valid JSON array. No markdown. No explanation:
[
  {{
    "pattern": "Senior ML Engineers with credit risk experience",
    "count": 6,
    "inferred_initiative": "Building in-house credit underwriting to reduce dependency on third-party bureaus — signals a lending or BNPL product in 3-6 months"
  }}
]

Rules:
- inferred_initiative must be specific and actionable — what product/feature does this signal?
- Include the "why" — why does this hiring pattern indicate this initiative?
- Return 3 to 6 patterns
- Focus on patterns that reveal product roadmap, not generic hiring"""


def product_prompt(company: str, context: str, tech_signals: list) -> str:
    return f"""You are a product intelligence analyst predicting {company}'s upcoming moves.

EVIDENCE FROM BLOG, GITHUB AND HIRING:
{context}

TECH SIGNALS ALREADY DETECTED: {[s.get('technology') for s in tech_signals]}

Based on all signals, what products or features is {company} most likely to launch next?

Return ONLY a valid JSON object. No markdown. No explanation:
{{
  "product_signals": [
    {{
      "feature": "Real-time fraud detection system",
      "evidence": "3 blog posts on ML pipelines + 4 ML engineer hires with fraud background + new 'risk-engine' GitHub repo",
      "launch_probability": 0.82,
      "timeline": "2-4 months"
    }}
  ],
  "ai_maturity": {{
    "score": 7.5,
    "notes": "Strong MLOps signals: custom feature store, A/B testing infrastructure, dedicated ML platform team of 8+. Not cutting-edge research but solid applied ML."
  }}
}}

Rules:
- launch_probability: 0.0 to 1.0 (only include if > 0.3)
- timeline: estimate based on hiring urgency and engineering depth ("1-2 months", "3-6 months", "6-12 months")
- ai_maturity score: 0-10 (0=no AI/ML, 10=frontier research company)
- evidence must cite actual signals — don't make things up
- Be bold with predictions — a VC pays for opinions, not hedges"""


def synthesis_prompt(company: str, tech: list, hiring: list, product: list,
                     ai_score: float, ai_notes: str) -> str:
    import json
    return f"""You are a Managing Director at a top VC firm writing a 5-minute intelligence brief on {company} for a partner meeting.

INTELLIGENCE GATHERED:
Tech Stack Signals: {json.dumps(tech, indent=2)}
Hiring Signals: {json.dumps(hiring, indent=2)}
Predicted Product Moves: {json.dumps(product, indent=2)}
AI/ML Maturity: {ai_score}/10 — {ai_notes}

Write a sharp, opinionated 4-paragraph executive brief covering:

Paragraph 1 — WHAT THEY'RE BUILDING NOW: Based on tech + hiring signals, what is {company} actively building? Be specific. Name technologies and initiatives.

Paragraph 2 — WHAT THEY'RE ABOUT TO LAUNCH: Your prediction for their next 3-6 months. Reference actual signals. Put a stake in the ground.

Paragraph 3 — AI/ML MATURITY ASSESSMENT: Where are they on the AI maturity curve vs competitors? What does their ML investment pattern tell you about their strategic bets?

Paragraph 4 — THE KEY RISK OR BLINDSPOT: What weakness or gap do you infer from the signals? What are they NOT doing that competitors are? What could hurt them?

Tone: Direct. Confident. No hedging. No generic statements. No "they seem to be" — say "they are". Write like you're briefing a partner before a $10M investment decision."""
