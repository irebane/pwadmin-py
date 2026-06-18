from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from app.deps import get_db, get_current_user, require_admin
from app.services.accounts import (
    list_accounts, load_account, save_account,
    add_gold, set_gm_rank, delete_account,
    load_account_v2, list_accounts_v2, account_tool_v2, account_save_v2,
)
from pydantic import BaseModel

router = APIRouter(prefix="/api/accounts")


# ── PHP-compatible endpoints (used by accounts.js) ───────────────────────


class LoadBody(BaseModel):
    id: int = 0


@router.post("/load")
async def account_load(
    body: LoadBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user.get("is_admin") and user.get("id") != body.id:
        return JSONResponse([{"error": "Unauthorized."}])
    result = await load_account_v2(db, body.id, viewer_is_admin=user.get("is_admin", False))
    return JSONResponse(result)


class ListBody(BaseModel):
    sname: str = ""
    stype: int = 1


@router.post("/list")
async def account_list_post(
    body: ListBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    result = await list_accounts_v2(db, body.sname, body.stype)
    return JSONResponse(result)


class ToolBody(BaseModel):
    tool: int = 0
    id: int = 0
    amount: int = 0
    day: int = 0
    bannerid: int = 0
    targetid: int = 0
    bantype: int = 0
    gmid: int = 0
    banreason: str = ""
    bandur: str = ""


@router.post("/tool")
async def account_tool_post(
    body: ToolBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    result = await account_tool_v2(db, body.tool, body.model_dump(), is_admin=True)
    return JSONResponse(result)


class SaveBody(BaseModel):
    NameStack: str = ""
    PasswordStack: str = ""
    Email: str = ""
    RealName: str = ""
    Gender: int = 0
    DateYMD: str = ""
    Rank: int = 0


@router.post("/save")
async def account_save_post(
    body: SaveBody,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    result = await account_save_v2(
        db, user,
        body.NameStack, body.PasswordStack,
        body.Email, body.RealName,
        body.Gender, body.DateYMD, body.Rank,
    )
    return JSONResponse(result)


# ── Legacy REST endpoints ────────────────────────────────────────────────


@router.get("")
async def accounts_list_legacy(
    search: str = Query("", max_length=64),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    return await list_accounts(db, search, page, page_size)


@router.get("/{user_id}")
async def account_get_legacy(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    if not user.get("is_admin") and user["id"] != user_id:
        raise HTTPException(403)
    return await load_account(db, user_id)


class SaveBodyLegacy(BaseModel):
    current_password: str = ""
    new_password: str = ""
    email: str = ""
    truename: str = ""
    sex: int = 0
    birthday: str = ""


@router.post("/{user_id}/save")
async def account_save_legacy(
    user_id: int,
    body: SaveBodyLegacy,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    error = await save_account(db, user, user_id, body.model_dump())
    if error:
        raise HTTPException(400, detail=error)
    return {"success": True}


class ToolBodyLegacy(BaseModel):
    action: str
    value: int = 0


@router.post("/{user_id}/tool")
async def account_tool_legacy(
    user_id: int,
    body: ToolBodyLegacy,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_admin),
):
    if body.action == "add_gold":
        return {"success": await add_gold(db, user_id, body.value)}
    elif body.action == "set_gm":
        return {"success": await set_gm_rank(db, user_id, body.value)}
    elif body.action == "delete":
        return {"success": await delete_account(db, user_id)}
    raise HTTPException(400, detail=f"Unknown action: {body.action}")
