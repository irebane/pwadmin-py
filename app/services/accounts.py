from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update
from app.models.users import User, Auth
from app.auth.passwords import hash_password_compat, verify_password_compat, validate_date
from app.config import settings


async def list_accounts(
    db: AsyncSession,
    search: str = "",
    page: int = 1,
    page_size: int = 50,
) -> dict:
    query = select(User)
    if search:
        query = query.where(User.name.like(f"{search}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    users = result.scalars().all()
    return {
        "users": [{"id": u.ID, "name": u.name, "email": u.email} for u in users],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def load_account(db: AsyncSession, user_id: int) -> dict | None:
    result = await db.execute(select(User).where(User.ID == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    return {
        "id": user.ID,
        "name": user.name,
        "email": user.email,
        "truename": user.truename or "",
        "gender": user.gender or 0,
        "birthday": str(user.birthday.date()) if user.birthday else "",
        "webpoint": user.WebPoint or 0,
        "votepoint": user.VotePoint or 0,
    }


async def save_account(
    db: AsyncSession,
    requesting_user: dict,
    target_id: int,
    data: dict,
) -> str:
    is_admin = requesting_user.get("is_admin", False)
    requesting_id = requesting_user["id"]
    if not is_admin and requesting_id != target_id:
        return "Unauthorized"

    result = await db.execute(select(User).where(User.ID == target_id))
    user = result.scalar_one_or_none()
    if not user:
        return "User not found"

    if data.get("new_password"):
        new_pw = data["new_password"]
        if not (4 < len(new_pw) < 21) or not new_pw.isalnum():
            return "Invalid password format"
        cur_pw = data.get("current_password", "")
        if not is_admin:
            if not verify_password_compat(user.name, cur_pw, user.passwd, settings.pass_type):
                return "Current password incorrect"
        user.passwd = hash_password_compat(user.name, new_pw, settings.pass_type)

    if data.get("email"):
        user.email = data["email"].lower().strip()
    if data.get("truename") is not None:
        user.truename = data["truename"].strip()
    if data.get("gender") is not None:
        user.gender = int(data["gender"])
    if data.get("birthday"):
        if validate_date(data["birthday"]):
            user.birthday = data["birthday"]

    await db.commit()
    return ""


async def add_gold(db: AsyncSession, user_id: int, amount: int) -> bool:
    await db.execute(
        update(User).where(User.ID == user_id).values(WebPoint=User.WebPoint + amount)
    )
    await db.commit()
    return True


async def set_gm_rank(db: AsyncSession, user_id: int, rank: int) -> bool:
    """GM rank is managed via the auth table (userid/zoneid/rid composite key).
    We only support a global toggle here — zone-specific GM management is out of scope."""
    if rank == 0:
        await db.execute(delete(Auth).where(Auth.userid == user_id))
    await db.commit()
    return True


async def delete_account(db: AsyncSession, user_id: int) -> bool:
    await db.execute(delete(User).where(User.ID == user_id))
    await db.commit()
    return True
