import ipaddress
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, update, text
from app.models.users import User, Auth, Forbid
from app.auth.passwords import hash_password_compat, verify_password_compat, validate_date
from app.config import settings


def _long2ip(n) -> str:
    try:
        return str(ipaddress.IPv4Address(int(n) & 0xFFFFFFFF))
    except Exception:
        return "0.0.0.0"


def _tool_resp(error="", success="", reloaduserdata="0", reloaduserlist="0"):
    return [{"error": error, "success": success,
             "reloaduserdata": reloaduserdata, "reloaduserlist": reloaduserlist}]


async def load_account_v2(db: AsyncSession, user_id: int, viewer_is_admin: bool = False) -> list:
    result = await db.execute(select(User).where(User.ID == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return [{"error": "User not found"}]

    is_gm = bool(await db.scalar(
        select(func.count()).where(Auth.userid == user_id)
    ))

    # session / zone data
    row = await db.execute(
        text("SELECT lastlogin, zoneid, zonelocalid FROM point WHERE uid=:uid LIMIT 1"),
        {"uid": user_id}
    )
    pt = row.fetchone()
    session_data = {
        "lastlogin": str(pt.lastlogin) if pt and pt.lastlogin else "",
        "zoneid": int(pt.zoneid) if pt and pt.zoneid is not None else 0,
        "zonelocalid": int(pt.zonelocalid) if pt and pt.zonelocalid is not None else 0,
    }

    # gold log — completed
    log_rows = await db.execute(
        text("SELECT cash, fintime FROM usecashlog WHERE userid=:uid ORDER BY fintime DESC LIMIT 30"),
        {"uid": user_id}
    )
    gold_log = {}
    idx = 0
    for r in log_rows.fetchall():
        gold_log[idx] = {"cash": int(r.cash), "fintime": str(r.fintime), "pending": 0}
        idx += 1

    # pending gold
    pend_rows = await db.execute(
        text("SELECT cash, creatime FROM usecashnow WHERE userid=:uid LIMIT 10"),
        {"uid": user_id}
    )
    for r in pend_rows.fetchall():
        gold_log[idx] = {"cash": int(r.cash), "fintime": str(r.creatime), "pending": 1}
        idx += 1

    # characters — gamedbd uses users.ID directly as the game account ID
    classes = settings.pw_classes_dict
    chars = {}
    import asyncio
    from app.pw_socket import get_user_roles, get_role_base
    loop = asyncio.get_event_loop()
    role_list = await loop.run_in_executor(None, get_user_roles, user_id)
    for i, role in enumerate(role_list):
        base = await loop.run_in_executor(None, get_role_base, role["role_id"], classes)
        chars[i] = {
            "roleid": role["role_id"],
            "rolename": role["role_name"],
            "roleclass": base["role_class"] if base else "",
            "rolepath": base["role_path"] if base else "",
            "rolelevel": base["role_level"] if base else 0,
            "posX": base["pos_x"] if base else 0,
            "posY": base["pos_y"] if base else 0,
            "posZ": base["pos_z"] if base else 0,
            "map": base["map"] if base else 0,
        }

    if user.birthday:
        try:
            bd = str(user.birthday.date()) + " 00:00:00"
        except AttributeError:
            bd = str(user.birthday)[:10] + " 00:00:00"
    else:
        bd = "0000-00-00 00:00:00"
    ct = str(user.creatime) if user.creatime else ""

    user_data = {
        "self": 0,
        "id": user.ID,
        "username": user.name,
        "password": user.passwd,
        "rank": 1 if is_gm else 0,
        "srank": 1 if viewer_is_admin else 0,
        "truename": user.truename or "",
        "email": user.email,
        "creatime": ct,
        "birthday": bd,
        "gender": user.gender or 0,
        "regIp": user.idnumber or "",
        "loginIp": _long2ip(user.mudev or 0),
        "votepoint": user.VotePoint or 0,
        "votedate": "",
        "pointtogold": settings.point_exc or 1,
    }

    return [{"error": ""}, user_data, session_data, gold_log, chars]


async def list_accounts_v2(db: AsyncSession, sname: str, stype: int) -> list:
    """
    stype: 1=all, 2=by IP, 3=by ID, 4=by name/truename, 5=by email,
           6=online (zoneid>0), 7=inactive N days, 8=GMs, 9=all GMs
    """
    users_out = {}

    if stype == 8 or stype == 9:
        gm_ids = (await db.execute(select(Auth.userid).distinct())).scalars().all()
        if not gm_ids:
            return [{"error": ""}, {}]
        query = select(User).where(User.ID.in_(gm_ids))
    elif stype == 6:
        online_ids = (await db.execute(
            text("SELECT uid FROM point WHERE zoneid>0")
        )).scalars().all()
        if not online_ids:
            return [{"error": ""}, {}]
        query = select(User).where(User.ID.in_(online_ids))
    elif stype == 7:
        # inactive for sname days
        try:
            days = int(sname)
        except Exception:
            days = 30
        cutoff = datetime.utcnow() - timedelta(days=days)
        stale_ids = (await db.execute(
            text("SELECT uid FROM point WHERE lastlogin < :cutoff"),
            {"cutoff": cutoff}
        )).scalars().all()
        if not stale_ids:
            return [{"error": ""}, {}]
        query = select(User).where(User.ID.in_(stale_ids))
    elif stype == 1 or sname == "":
        query = select(User).limit(100)
    elif stype == 3:
        try:
            uid = int(sname)
        except Exception:
            return [{"error": "Invalid ID"}]
        query = select(User).where(User.ID == uid)
    elif stype == 4:
        query = select(User).where(
            (User.name.like(f"%{sname}%")) | (User.truename.like(f"%{sname}%"))
        ).limit(50)
    elif stype == 5:
        query = select(User).where(User.email.like(f"%{sname}%")).limit(50)
    elif stype == 2:
        # by IP — idnumber (reg IP) or mudev (last login IP as int)
        try:
            ip_int = int(ipaddress.IPv4Address(sname))
        except Exception:
            ip_int = 0
        query = select(User).where(
            (User.idnumber == sname) | (User.mudev == ip_int)
        ).limit(50)
    else:
        query = select(User).limit(100)

    rows = (await db.execute(query)).scalars().all()

    # get online zone IDs
    online_map = {}
    if rows:
        from app.models.users import Point
        uid_list = [u.ID for u in rows]
        pts = await db.execute(select(Point.uid, Point.zoneid).where(Point.uid.in_(uid_list)))
        online_map = {r.uid: (r.zoneid or 0) for r in pts.fetchall()}

    gm_ids_set = set((await db.execute(select(Auth.userid).distinct())).scalars().all())

    for i, u in enumerate(rows):
        users_out[i] = {
            "userid": u.ID,
            "username": u.name,
            "realname": u.truename or "",
            "rank": 1 if u.ID in gm_ids_set else 0,
            "email": u.email,
            "zoneid": online_map.get(u.ID, 0),
            "ip": u.idnumber or "",
            "loginIp": _long2ip(u.mudev or 0),
        }

    return [{"error": ""}, users_out]


async def account_tool_v2(db: AsyncSession, tool: int, params: dict, is_admin: bool) -> list:
    if not is_admin:
        return _tool_resp(error="Admin access required.")

    uid = int(params.get("id", 0))
    amount = int(params.get("amount", 0))

    if tool == 2:  # add gold
        if uid < 1 or amount < 1:
            return _tool_resp(error="Invalid parameters.")
        uname = await db.scalar(select(User.name).where(User.ID == uid)) or "unknown"
        await db.execute(update(User).where(User.ID == uid).values(
            WebPoint=func.coalesce(User.WebPoint, 0) + amount))
        await db.commit()
        return _tool_resp(success=f"Added {amount} gold to account: {uname} [{uid}]",
                          reloaduserdata="1")

    elif tool == 3:  # add vote point
        if uid < 1 or amount < 1:
            return _tool_resp(error="Invalid parameters.")
        await db.execute(update(User).where(User.ID == uid).values(VotePoint=User.VotePoint + amount))
        await db.commit()
        return _tool_resp(success=f"Added {amount} points to account {uid}.",
                          reloaduserdata="1")

    elif tool == 4:  # add GM
        if uid < 1:
            return _tool_resp(error="Invalid user ID.")
        existing = await db.scalar(select(func.count()).where(Auth.userid == uid))
        if not existing:
            db.add(Auth(userid=uid, zoneid=0, rid=1))
            await db.commit()
        return _tool_resp(success=f"GM rank granted to {uid}.",
                          reloaduserdata="1", reloaduserlist="1")

    elif tool == 5:  # remove GM
        if uid < 1:
            return _tool_resp(error="Invalid user ID.")
        await db.execute(delete(Auth).where(Auth.userid == uid))
        await db.commit()
        return _tool_resp(success=f"GM rank removed from {uid}.",
                          reloaduserdata="1", reloaduserlist="1")

    elif tool == 6:  # ban/unban character (requires live game server)
        return _tool_resp(error="Character ban requires the game server to be online. Use the game GM tools.")

    elif tool == 8:  # delete account
        if uid < 1:
            return _tool_resp(error="Invalid user ID.")
        await db.execute(delete(Auth).where(Auth.userid == uid))
        await db.execute(delete(Forbid).where(Forbid.userid == uid))
        await db.execute(delete(User).where(User.ID == uid))
        await db.commit()
        return _tool_resp(success=f"Account {uid} deleted.", reloaduserlist="1")

    elif tool == 9:  # delete inactive accounts older than N days
        days = int(params.get("day", 365))
        cutoff = datetime.utcnow() - timedelta(days=days)
        stale = (await db.execute(
            text("SELECT uid FROM point WHERE lastlogin < :cutoff"), {"cutoff": cutoff}
        )).scalars().all()
        if not stale:
            return _tool_resp(success="No inactive accounts found.", reloaduserlist="1")
        for uid_ in stale:
            await db.execute(delete(Auth).where(Auth.userid == uid_))
            await db.execute(delete(Forbid).where(Forbid.userid == uid_))
            await db.execute(delete(User).where(User.ID == uid_))
        await db.commit()
        return _tool_resp(success=f"Deleted {len(stale)} inactive accounts.", reloaduserlist="1")

    elif tool == 10:  # reward active users with gold
        days = int(params.get("day", 1))
        reward = int(params.get("amount", 0))
        if reward < 1:
            return _tool_resp(error="Invalid reward amount.")
        cutoff = datetime.utcnow() - timedelta(days=days)
        active = (await db.execute(
            text("SELECT uid FROM point WHERE lastlogin >= :cutoff"), {"cutoff": cutoff}
        )).scalars().all()
        if not active:
            return _tool_resp(success="No active accounts in that period.", reloaduserlist="1")
        await db.execute(
            update(User).where(User.ID.in_(active)).values(WebPoint=User.WebPoint + reward)
        )
        await db.commit()
        return _tool_resp(success=f"Gave {reward} gold to {len(active)} active accounts.",
                          reloaduserlist="1")

    elif tool == 11:  # reward active users with vote points
        days = int(params.get("day", 1))
        reward = int(params.get("amount", 0))
        if reward < 1:
            return _tool_resp(error="Invalid reward amount.")
        cutoff = datetime.utcnow() - timedelta(days=days)
        active = (await db.execute(
            text("SELECT uid FROM point WHERE lastlogin >= :cutoff"), {"cutoff": cutoff}
        )).scalars().all()
        if not active:
            return _tool_resp(success="No active accounts in that period.", reloaduserlist="1")
        await db.execute(
            update(User).where(User.ID.in_(active)).values(VotePoint=User.VotePoint + reward)
        )
        await db.commit()
        return _tool_resp(success=f"Gave {reward} points to {len(active)} active accounts.",
                          reloaduserlist="1")

    return _tool_resp(error=f"Unknown tool: {tool}")


async def account_save_v2(
    db: AsyncSession,
    requesting_user: dict,
    name_stack: str,
    pw_stack: str,
    email: str,
    realname: str,
    gender: int,
    date_ymd: str,
    rank: int,
) -> list:
    is_admin = requesting_user.get("is_admin", False)

    # parse name stack: "CurUnam-CurUId-OldUnam-OldUId"
    parts = name_stack.split("-")
    if len(parts) < 4:
        return _tool_resp(error="Invalid request format.")
    cur_unam, cur_uid_s, old_unam, old_uid_s = parts[0], parts[1], parts[2], parts[3]
    try:
        target_id = int(cur_uid_s)
        old_id = int(old_uid_s)
    except ValueError:
        return _tool_resp(error="Invalid user ID.")

    if not is_admin and requesting_user.get("id") != old_id:
        return _tool_resp(error="Unauthorized.")

    result = await db.execute(select(User).where(User.ID == old_id))
    user = result.scalar_one_or_none()
    if not user:
        return _tool_resp(error="User not found.")

    # parse pw stack: "CurPwd-NewPwd1-NewPwd2"
    pw_parts = pw_stack.split("-")
    cur_pwd = pw_parts[0] if len(pw_parts) > 0 else ""
    new_pwd1 = pw_parts[1] if len(pw_parts) > 1 else ""
    new_pwd2 = pw_parts[2] if len(pw_parts) > 2 else ""

    if new_pwd1 and new_pwd1 != cur_pwd:
        if new_pwd1 != new_pwd2:
            return _tool_resp(error="New passwords do not match.")
        if not is_admin:
            # Accept either: stored hash sent back as-is, or plain-text password that hashes to match
            valid = (cur_pwd == user.passwd) or verify_password_compat(user.name, cur_pwd, user.passwd, settings.pass_type)
            if not valid:
                return _tool_resp(error="Current password is incorrect.")
        user.passwd = hash_password_compat(user.name, new_pwd1, settings.pass_type)

    if email:
        user.email = email.lower().strip()
    if realname is not None:
        user.truename = realname.strip()
    if gender in (0, 1, 2):
        user.gender = gender

    if date_ymd and date_ymd != "0000-00-00":
        if validate_date(date_ymd):
            user.birthday = date_ymd

    # rename
    if is_admin and cur_unam and cur_unam != old_unam:
        exists = await db.scalar(select(func.count()).where(User.name == cur_unam.lower()))
        if exists:
            return _tool_resp(error="Username already taken.")
        user.name = cur_unam.lower()
        user.passwd = hash_password_compat(user.name, new_pwd1 or cur_pwd, settings.pass_type)

    # change UID (admin only, dangerous)
    if is_admin and target_id != old_id:
        exists = await db.scalar(select(func.count()).where(User.ID == target_id))
        if exists:
            return _tool_resp(error="User ID already taken.")
        user.ID = target_id

    # GM rank
    if is_admin:
        existing_gm = await db.scalar(select(func.count()).where(Auth.userid == old_id))
        if rank == 1 and not existing_gm:
            db.add(Auth(userid=old_id, zoneid=0, rid=1))
        elif rank == 0 and existing_gm:
            await db.execute(delete(Auth).where(Auth.userid == old_id))

    await db.commit()
    return _tool_resp(success="Account updated successfully.",
                      reloaduserdata="1", reloaduserlist="1")


# Legacy helpers kept for other code that may call them
async def list_accounts(db, search="", page=1, page_size=50):
    query = select(User)
    if search:
        query = query.where(User.name.like(f"{search}%"))
    total = await db.scalar(select(func.count()).select_from(query.subquery()))
    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size))
    users = result.scalars().all()
    return {"users": [{"id": u.ID, "name": u.name, "email": u.email} for u in users],
            "total": total, "page": page, "page_size": page_size}


async def load_account(db, user_id):
    result = await db.execute(select(User).where(User.ID == user_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    return {"id": user.ID, "name": user.name, "email": user.email,
            "truename": user.truename or "", "gender": user.gender or 0,
            "birthday": str(user.birthday.date()) if user.birthday else "",
            "webpoint": user.WebPoint or 0, "votepoint": user.VotePoint or 0}


async def save_account(db, requesting_user, target_id, data):
    is_admin = requesting_user.get("is_admin", False)
    if not is_admin and requesting_user["id"] != target_id:
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


async def add_gold(db, user_id, amount):
    await db.execute(update(User).where(User.ID == user_id).values(WebPoint=User.WebPoint + amount))
    await db.commit()
    return True


async def set_gm_rank(db, user_id, rank):
    if rank == 0:
        await db.execute(delete(Auth).where(Auth.userid == user_id))
    await db.commit()
    return True


async def delete_account(db, user_id):
    await db.execute(delete(User).where(User.ID == user_id))
    await db.commit()
    return True
