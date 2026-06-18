from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.deps import get_db, require_admin
from app.models.audit import ActivityLog
from pydantic import BaseModel

router = APIRouter(prefix="/api/activity-log")


@router.get("")
async def get_log(
    limit: int = Query(100, le=500),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    result = await db.execute(
        select(ActivityLog).order_by(desc(ActivityLog.timestamp)).limit(limit)
    )
    entries = result.scalars().all()
    return [
        {
            "id": e.id,
            "timestamp": e.timestamp.isoformat(),
            "admin_user": e.admin_user,
            "action": e.action,
            "params": e.params,
            "result": e.result,
        }
        for e in entries
    ]


class LogEntry(BaseModel):
    action: str
    params: dict = {}
    result: str = ""


@router.post("")
async def add_log(
    body: LogEntry,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    entry = ActivityLog(
        admin_user=user["name"],
        action=body.action,
        params=body.params,
        result=body.result,
    )
    db.add(entry)
    await db.commit()
    return {"success": True}
