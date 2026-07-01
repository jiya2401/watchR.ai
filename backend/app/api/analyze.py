import uuid
from datetime import datetime
from fastapi import APIRouter, BackgroundTasks, HTTPException
from app.database import get_db
from app.models.schemas import AnalyzeResponse, Report, JobStatus

router = APIRouter()


@router.post("/{company}", response_model=AnalyzeResponse)
async def trigger_analysis(company: str, background_tasks: BackgroundTasks, force: bool = False):
    """
    Start full WatchR analysis for a company.
    Returns job_id immediately. Frontend polls /status or subscribes to /ws.
    """
    db = get_db()
    company = company.strip()

    if not force:
        # Check for recent report (< 24 hours old)
        from datetime import timedelta
        recent = await db.reports.find_one({
            "company": company,
            "status": JobStatus.DONE,
            "created_at": {"$gte": datetime.utcnow() - timedelta(hours=24)},
        })
        if recent:
            return AnalyzeResponse(
                job_id=recent["job_id"],
                company=company,
                message="Recent report found (< 24h old). Use force=true to re-analyze.",
                ws_url=f"/ws/agent/{recent['job_id']}",
            )

    # Upsert company
    await db.companies.update_one(
        {"name": company},
        {"$setOnInsert": {
            "name": company,
            "created_at": datetime.utcnow(),
            "report_count": 0,
            "status": "pending",
        }},
        upsert=True,
    )

    job_id = str(uuid.uuid4())

    # Create empty report document
    await db.reports.insert_one({
        "job_id":            job_id,
        "company":           company,
        "status":            JobStatus.PENDING,
        "step_log":          [],
        "tech_signals":      [],
        "hiring_signals":    [],
        "product_signals":   [],
        "ai_maturity_score": 0.0,
        "ai_maturity_notes": "",
        "executive_summary": "",
        "sources_used":      [],
        "articles_scraped":  0,
        "created_at":        datetime.utcnow(),
        "error":             "",
    })

    background_tasks.add_task(_run_agent, company, job_id)

    return AnalyzeResponse(
        job_id=job_id,
        company=company,
        message=f"Analysis started for {company}",
        ws_url=f"/ws/agent/{job_id}",
    )


@router.get("/{company}/report", response_model=Report | None)
async def get_latest_report(company: str):
    """Get the most recent completed report."""
    doc = await get_db().reports.find_one(
        {"company": company, "status": JobStatus.DONE},
        sort=[("created_at", -1)],
    )
    if not doc:
        return None
    doc.pop("_id", None)
    return Report(**doc)


@router.get("/{company}/reports", response_model=list[Report])
async def get_all_reports(company: str):
    """Get all historical reports for trend tracking."""
    out = []
    async for doc in get_db().reports.find(
        {"company": company},
        sort=[("created_at", -1)],
        limit=10,
    ):
        doc.pop("_id", None)
        out.append(Report(**doc))
    return out


@router.get("/{company}/status")
async def get_status(company: str):
    """
    Poll this endpoint to get current agent status and step logs.
    Used by WebSocket fallback and status checking.
    """
    doc = await get_db().reports.find_one(
        {"company": company},
        sort=[("created_at", -1)],
        projection={"job_id": 1, "status": 1, "step_log": 1,
                    "articles_scraped": 1, "sources_used": 1, "_id": 0},
    )
    if not doc:
        raise HTTPException(404, "No report found for this company")
    return doc


async def _run_agent(company: str, job_id: str) -> None:
    """Background task wrapper with error handling."""
    from app.agent.graph import run_agent
    try:
        await run_agent(company, job_id)
    except Exception as e:
        from app.utils.logger import get_logger
        get_logger(__name__).error("Agent failed: %s", e)
