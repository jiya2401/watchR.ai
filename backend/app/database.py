from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import IndexModel, ASCENDING, DESCENDING
from app.config import get_settings
from app.utils.logger import get_logger

log = get_logger(__name__)
settings = get_settings()

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_db() -> None:
    global _client, _db
    _client = AsyncIOMotorClient(
        settings.mongo_uri,
        serverSelectionTimeoutMS=5000,
        maxPoolSize=20,
    )
    _db = _client[settings.mongo_db]
    await _client.admin.command("ping")
    log.info("MongoDB connected → %s", settings.mongo_db)
    await _ensure_indexes()


async def disconnect_db() -> None:
    global _client
    if _client:
        _client.close()
        log.info("MongoDB disconnected")


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("DB not initialized — call connect_db() first")
    return _db


async def _ensure_indexes() -> None:
    db = get_db()

    await db.companies.create_indexes([
        IndexModel([("name", ASCENDING)], unique=True),
        IndexModel([("created_at", DESCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    await db.reports.create_indexes([
        IndexModel([("job_id", ASCENDING)], unique=True),
        IndexModel([("company", ASCENDING), ("created_at", DESCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ])

    await db.raw_data.create_indexes([
        IndexModel([("company", ASCENDING), ("source", ASCENDING)]),
        IndexModel([("scraped_at", DESCENDING)]),
    ])

    log.info("MongoDB indexes ensured")
