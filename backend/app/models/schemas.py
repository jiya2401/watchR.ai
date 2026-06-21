"""
app/models/schemas.py
All data models for WatchR.
"""
from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# Enums

class JobStatus(str, Enum):
    PENDING   = "pending"
    RUNNING   = "running"
    DONE      = "done"
    FAILED    = "failed"


class Source(str, Enum):
    BLOG   = "blog"
    GITHUB = "github"
    NEWS   = "news"
    JOBS   = "jobs"


# Signal models 

class TechSignal(BaseModel):
    technology: str
    evidence: str
    confidence: float          # 0.0 – 1.0
    signal_type: str           # adopting | scaling | retiring


class HiringSignal(BaseModel):
    pattern: str
    count: int
    inferred_initiative: str


class ProductSignal(BaseModel):
    feature: str
    evidence: str
    launch_probability: float  # 0.0 – 1.0
    timeline: str              # "2-3 months"


class StepLog(BaseModel):
    step: str
    message: str
    preview: str = ""
    ts: datetime = Field(default_factory=datetime.utcnow)


# Core models

class Company(BaseModel):
    name: str
    description: str = ""
    website: str = ""
    status: JobStatus = JobStatus.PENDING
    last_scraped: datetime | None = None
    report_count: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Report(BaseModel):
    job_id: str
    company: str
    status: JobStatus = JobStatus.PENDING
    # Signals
    tech_signals: list[TechSignal] = []
    hiring_signals: list[HiringSignal] = []
    product_signals: list[ProductSignal] = []
    # Analysis
    ai_maturity_score: float = 0.0
    ai_maturity_notes: str = ""
    executive_summary: str = ""
    # Meta
    step_log: list[StepLog] = []
    sources_used: list[str] = []
    articles_scraped: int = 0
    github_repos: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    error: str = ""


# API shapes 

class AnalyzeResponse(BaseModel):
    job_id: str
    company: str
    message: str
    ws_url: str

 
class WSMessage(BaseModel):
    type: str                   # step | done | failed | ping
    step: str = ""
    message: str = ""
    preview: str = ""
    data: dict[str, Any] = {}
    ts: datetime = Field(default_factory=datetime.utcnow)
