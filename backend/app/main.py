import asyncio
import json
from contextlib import asynccontextmanager 

import redis.asyncio as aioredis
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import get_settings
from app.database import connect_db, disconnect_db, get_db
from app.api.companies import router as companies_router
from app.api.analyze import router as analyze_router
from app.utils.logger import get_logger

log = get_logger(__name__)
settings = get_settings() 


# Lifespan 
@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("watchR.ai API starting up...")
    await connect_db()
    log.info("watchR.ai API ready ✓")
    yield
    await disconnect_db()
    log.info("watchR.ai API shutdown")


# App 
app = FastAPI(
    title="watchR.ai — Competitive Intelligence API",
    description="Autonomous competitive intelligence agent for Indian startups",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc", 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers 
app.include_router(companies_router, prefix="/api/companies", tags=["Companies"])
app.include_router(analyze_router,   prefix="/api/analyze",   tags=["Intelligence"])


# Health
@app.get("/health", tags=["System"])
async def health():
    checks = {"status": "ok", "service": "watchr-api", "version": "1.0.0"}

    try:
        await get_db().command("ping")
        checks["mongo"] = "ok"
    except Exception as e:
        checks["mongo"] = f"error: {e}"
        checks["status"] = "degraded"

    try:
        r = aioredis.from_url(settings.redis_url, socket_timeout=2)
        await r.ping()
        await r.aclose()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {e}"
        checks["status"] = "degraded"

    return checks


@app.get("/", tags=["System"])
async def root():
    return {
        "name": "watchR.ai API",
        "description": "Autonomous competitive intelligence for Indian startups",
        "docs": "/docs",
        "health": "/health",
    }


# WebSocket
@app.websocket("/ws/agent/{job_id}")
async def ws_agent_stream(websocket: WebSocket, job_id: str):
    """
    Real-time agent thought stream.
    Polls MongoDB for new step_log entries every 2 seconds
    and pushes them to the connected frontend.

    Frontend receives:
      {type: "step", step, message, preview}  — agent progress
      {type: "done"}                          — report complete
      {type: "failed", error}                 — something went wrong
      {type: "ping"}                          — keepalive
    """
    await websocket.accept()
    log.info("WS connected: job %s", job_id[:8])

    await websocket.send_json({"type": "connected", "job_id": job_id})

    last_log_count = 0
    idle_ticks = 0
    max_idle = 300  # 300 × 2s = 10 minutes max

    try:
        while idle_ticks < max_idle:
            await asyncio.sleep(2)
            idle_ticks += 1

            try:
                doc = await get_db().reports.find_one(
                    {"job_id": job_id},
                    {"step_log": 1, "status": 1, "error": 1, "_id": 0},
                )
            except Exception:
                continue

            if not doc:
                await websocket.send_json({"type": "ping"})
                continue

            status = doc.get("status", "pending")
            logs = doc.get("step_log", [])

            # Push any new log entries
            if len(logs) > last_log_count:
                for entry in logs[last_log_count:]:
                    await websocket.send_json({
                        "type":    "step",
                        "step":    entry.get("step", ""),
                        "message": entry.get("message", ""),
                        "preview": entry.get("preview", ""),
                    })
                    idle_ticks = 0  # reset idle on activity
                last_log_count = len(logs)

            # Terminal states
            if status == "done":
                await websocket.send_json({"type": "done"})
                log.info("WS: job %s complete", job_id[:8])
                break
            elif status == "failed":
                await websocket.send_json({
                    "type":  "failed",
                    "error": doc.get("error", "Unknown error"),
                })
                log.warning("WS: job %s failed", job_id[:8])
                break

            # Keepalive ping every 30s
            if idle_ticks % 15 == 0:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        log.info("WS disconnected: job %s", job_id[:8])
    except Exception as e:
        log.error("WS error: %s", e)
        try:
            await websocket.send_json({"type": "failed", "error": str(e)})
        except Exception:
            pass
