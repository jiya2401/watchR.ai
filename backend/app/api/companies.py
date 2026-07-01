from datetime import datetime
from fastapi import APIRouter, HTTPException, status
from app.database import get_db
from app.models.schemas import Company

router = APIRouter()


@router.get("/", response_model=list[Company])
async def list_companies():
    """List all tracked companies, newest first."""
    out = []
    async for doc in get_db().companies.find().sort("created_at", -1).limit(100):
        doc.pop("_id", None)
        out.append(Company(**doc))
    return out


@router.post("/", status_code=status.HTTP_201_CREATED, response_model=Company)
async def add_company(name: str, description: str = "", website: str = ""):
    db = get_db()
    name = name.strip()
    if not name:
        raise HTTPException(400, "Company name cannot be empty")
    if await db.companies.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}}):
        raise HTTPException(409, f"'{name}' is already being tracked")
    doc = {
        "name": name, "description": description, "website": website,
        "status": "pending", "report_count": 0,
        "last_scraped": None, "created_at": datetime.utcnow(),
    }
    await db.companies.insert_one(doc)
    doc.pop("_id", None)
    return Company(**doc)


@router.get("/{name}", response_model=Company)
async def get_company(name: str):
    doc = await get_db().companies.find_one({"name": {"$regex": f"^{name}$", "$options": "i"}})
    if not doc:
        raise HTTPException(404, f"Company '{name}' not found")
    doc.pop("_id", None)
    return Company(**doc)


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(name: str):
    db = get_db()
    r = await db.companies.delete_one({"name": name})
    if r.deleted_count == 0:
        raise HTTPException(404, f"Company '{name}' not found")
    # Clean up all associated data
    await db.raw_data.delete_many({"company": name})
    await db.reports.delete_many({"company": name})
