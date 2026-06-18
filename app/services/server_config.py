import re
import os
import asyncio
from pathlib import Path
from app.config import settings


def _server_file_path(key: int, filename: str) -> Path:
    """Resolve path from SERVER_FILES[key] entry (format: 'folder*daemon')."""
    entry = settings.server_files_dict.get(key, "")
    folder = entry.split("*")[0] if "*" in entry else entry
    return Path(settings.server_path.rstrip("/")) / folder / filename


async def read_conf(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


async def write_conf_atomic(path: Path, content: str) -> None:
    """Write via temp file + atomic rename."""
    tmp = str(path) + ".tmp"
    path.parent.mkdir(parents=True, exist_ok=True)
    Path(tmp).write_text(content, encoding="utf-8")
    os.replace(tmp, str(path))


def parse_conf_key(content: str, key: str) -> str | None:
    """Extract value for 'key = value' line (case-insensitive key match)."""
    for line in content.splitlines():
        stripped = line.strip().lower()
        if stripped.startswith(key.lower()):
            parts = line.split("=", 1)
            if len(parts) == 2:
                return parts[1].strip()
    return None


def update_conf_key(content: str, key: str, value: str) -> str:
    """Replace 'key = <old>' with 'key = <value>' in config content."""
    pattern = re.compile(rf"^({re.escape(key)}\s*=\s*).*$", re.IGNORECASE | re.MULTILINE)
    if pattern.search(content):
        return pattern.sub(rf"\g<1>{value}", content)
    return content + f"\n{key} = {value}\n"


# CMVal: class index → bit value in allow_login_class_mask
_CM_VAL = {1: 1, 2: 2, 3: 16, 4: 8, 5: 128, 6: 64, 7: 4, 8: 32}


def _read_threadpool_workers(path: Path) -> int | None:
    try:
        in_tp = False
        for ln in path.read_text().splitlines():
            ln = ln.strip()
            if ln.lower() == "[threadpool]":
                in_tp = True
            elif in_tp and ln.startswith("["):
                break
            elif in_tp and ln.lower().startswith("threads"):
                m = re.search(r'\(1,(\d+)\)', ln)
                if m:
                    return int(m.group(1))
    except Exception:
        pass
    return None


def _read_glinkd_count_from_conf() -> int:
    path = Path(settings.server_path) / "gamed" / "gmserver.conf"
    try:
        in_ps = False
        for ln in path.read_text().splitlines():
            ln = ln.strip()
            if ln.lower() == "[providerservers]":
                in_ps = True
            elif in_ps and ln.startswith("["):
                break
            elif in_ps and ln.lower().startswith("count="):
                return max(1, int(ln[6:]) - 2)
    except Exception:
        pass
    return 2


async def read_game_config() -> dict:
    result = {}
    init_log = []
    classes_data = settings.pw_classes_dict  # {int: name}

    try:
        ptemplate = _server_file_path(9, "ptemplate.conf")
        content = await read_conf(ptemplate)
        debug_val = (parse_conf_key(content, "debug_command_mode") or "").lower()
        result["debug_mode"] = int(debug_val in ("active", "1"))
        result["class_mask"] = int(parse_conf_key(content, "allow_login_class_mask") or 0)
        result["exp_bonus"] = int(parse_conf_key(content, "exp_bonus") or 0)
        result["sp_bonus"] = int(parse_conf_key(content, "sp_bonus") or 0)
        result["drop_bonus"] = int(parse_conf_key(content, "drop_bonus") or 0)
        result["money_bonus"] = int(parse_conf_key(content, "money_bonus") or 0)
        init_log.append("ptemplate.conf loaded")
    except Exception:
        init_log.append(f"Error: ptemplate.conf not found — check SERVER_PATH in .env")

    try:
        gamesys = _server_file_path(7, "gamesys.conf")
        content = await read_conf(gamesys)
        result["pvp"] = int(parse_conf_key(content, "pvp") or 0)
        result["tw"] = int(parse_conf_key(content, "battlefield") or 0)
        result["name_max_len"] = int(parse_conf_key(content, "max_name_len") or 16)
        result["name_insens"] = int(parse_conf_key(content, "case_insensitive") or 0)
        init_log.append("gamesys.conf loaded")
    except Exception:
        init_log.append("Warning: gamesys.conf not readable")

    glinkd_count = _read_glinkd_count_from_conf()
    result["glinkd_count"] = glinkd_count
    init_log.append(f"gmserver.conf: {glinkd_count} glinkd instance(s)")

    db_w = _read_threadpool_workers(Path(settings.server_path) / "gamedbd" / "gamesys.conf")
    result["db_workers"] = db_w if db_w is not None else 2
    if db_w is not None:
        init_log.append(f"gamedbd: {db_w} worker(s)")

    name_w = _read_threadpool_workers(Path(settings.server_path) / "uniquenamed" / "gamesys.conf")
    result["name_workers"] = name_w if name_w is not None else 1
    if name_w is not None:
        init_log.append(f"uniquenamed: {name_w} worker(s)")

    mask = result.get("class_mask", 0)
    result["classes"] = [
        {
            "id": i,
            "name": classes_data.get(i, f"Class{i}"),
            "value": _CM_VAL.get(i, 0),
            "checked": bool(mask & _CM_VAL.get(i, 0)),
        }
        for i in range(1, len(classes_data) + 1)
        if i in classes_data
    ]
    result["init_log"] = init_log

    return result


async def save_game_config(data: dict) -> str:
    """Write values to the config files. Returns '' on success or error message."""
    try:
        ptemplate = _server_file_path(9, "ptemplate.conf")
        content = await read_conf(ptemplate)
        debug_str = "active" if data.get("debug_mode") else "0"
        for k, v in [
            ("debug_command_mode", debug_str),
            ("allow_login_class_mask", str(data.get("class_mask", 0))),
            ("exp_bonus", str(data.get("exp_bonus", 0))),
            ("sp_bonus", str(data.get("sp_bonus", 0))),
            ("drop_bonus", str(data.get("drop_bonus", 0))),
            ("money_bonus", str(data.get("money_bonus", 0))),
        ]:
            content = update_conf_key(content, k, v)
        await write_conf_atomic(ptemplate, content)

        gamesys = _server_file_path(7, "gamesys.conf")
        content = await read_conf(gamesys)
        for k, v in [
            ("battlefield", str(data.get("tw", 0))),
            ("pvp", str(data.get("pvp", 0))),
            ("max_name_len", str(data.get("name_max_len", 16))),
        ]:
            content = update_conf_key(content, k, v)
        await write_conf_atomic(gamesys, content)

        gamesys2 = _server_file_path(2, "gamesys.conf")
        content = await read_conf(gamesys2)
        content = update_conf_key(content, "case_insensitive", str(data.get("name_insens", 0)))
        await write_conf_atomic(gamesys2, content)

        glinkd_count = max(1, int(data.get("glinkd_count", 1)))
        await _rebuild_gamesys_conf(glinkd_count)
        await _rebuild_gmserver_conf(glinkd_count, str(_server_file_path(7, "gmserver.conf")))
        await _rebuild_start_sh(glinkd_count)

        gamedbd_conf = _server_file_path(7, "gamesys.conf")
        db_workers = max(1, int(data.get("db_workers", 1)))
        content = gamedbd_conf.read_text()
        content = re.sub(r'(\(1,)\d+(\))', rf'\g<1>{db_workers}\2', content)
        await write_conf_atomic(gamedbd_conf, content)

        return ""
    except Exception as e:
        return str(e)


async def _rebuild_gamesys_conf(glinkd_count: int) -> None:
    path = Path("/home/glinkd/gamesys.conf")
    if not path.exists():
        return
    content = path.read_text()
    parts = re.split(r'^(?=\[)', content, flags=re.MULTILINE)
    fixed = {}
    for part in parts:
        m = re.match(r'^\[([^\]]+)\]', part)
        sname = m.group(1) if m else ""
        if not re.match(r'^(GLinkServer|GProviderServer)\d+$', sname):
            fixed[sname] = part.rstrip()
    gs_out = ""
    for n in range(1, glinkd_count + 1):
        p = 29000 + n - 1
        gs_out += (
            f"[GLinkServer{n}]\ntype\t\t\t=\ttcp\nport\t\t\t=\t{p}\naddress\t\t\t=\t0.0.0.0\n"
            "so_sndbuf\t\t=\t12288\nso_rcvbuf\t\t=\t12288\nibuffermax\t\t=\t16384\nobuffermax\t\t=\t65536\n"
            "tcp_nodelay\t\t=\t0\nlisten_backlog\t=\t10\naccumulate\t\t=\t131072\nmax_users\t\t=\t3000\n"
            "halflogin_users\t=\t6000\nsender_interval\t=\t200000\naccumu_packets\t=\t32768\n"
            "mtrace\t\t\t=\t/tmp/m_trace.link\ncompress\t\t=\t0\nclose_discard\t=\t1\n"
            "urgency_support\t=\t1\nversion=10402\n\n"
        )
    if "GDeliveryClient" in fixed:
        gs_out += fixed["GDeliveryClient"] + "\n\n"
    for n in range(1, glinkd_count + 1):
        p = 29300 + n
        gs_out += (
            f"[GProviderServer{n}]\ntype\t\t\t=\ttcp\nport\t\t\t=\t{p}\naddress\t\t\t=\t0.0.0.0\n"
            "so_sndbuf\t\t=\t65536\nso_rcvbuf\t\t=\t65536\nibuffermax\t\t=\t1048576\nobuffermax\t\t=\t1048576\n"
            "tcp_nodelay\t\t=\t0\naccumulate\t\t=\t268435456\n\n"
        )
    for k in ["GFactionClient", "LogclientClient", "LogclientTcpClient", "ThreadPool"]:
        if k in fixed:
            gs_out += fixed[k] + "\n\n"
    await write_conf_atomic(path, gs_out.rstrip() + "\n")


async def _rebuild_gmserver_conf(glinkd_count: int, path_str: str) -> None:
    path = Path(path_str)
    if not path.exists():
        return
    content = path.read_text()
    parts = re.split(r'^(?=\[)', content, flags=re.MULTILINE)
    fixed = {}
    for part in parts:
        m = re.match(r'^\[([^\]]+)\]', part)
        sname = m.group(1) if m else ""
        if sname == "ProviderServers" or re.match(r'^GProviderClient\d+$', sname):
            continue
        fixed[sname] = part.rstrip()
    total = glinkd_count + 2
    gm_out = (
        f"[ProviderServers]\ncount={total}\n\n"
        "[GProviderClient0]\n;this must be delivery server\ntype\t\t\t=\ttcp\nport\t\t\t=\t29300\n"
        "address\t\t\t=\t127.0.0.1\nso_sndbuf\t\t=\t65536\nso_rcvbuf\t\t=\t65536\n"
        "ibuffermax\t\t=\t1048576\nobuffermax\t\t=\t1048576\ntcp_nodelay\t\t=\t1\n"
        "listen_backlog\t=\t10\naccumulate\t\t=\t104857600\n\n"
        "[GProviderClient1]\n;this is factionserver\ntype\t\t\t=\ttcp\nport\t\t\t=\t29600\n"
        "address\t\t\t=\t127.0.0.1\nso_sndbuf\t\t=\t65536\nso_rcvbuf\t\t=\t65536\n"
        "ibuffermax\t\t=\t1048576\nobuffermax\t\t=\t1048576\ntcp_nodelay\t\t=\t1\n"
        "listen_backlog\t=\t10\naccumulate\t\t=\t104857600\n\n"
    )
    for n in range(1, glinkd_count + 1):
        idx = n + 1
        port = 29300 + n
        gm_out += (
            f"[GProviderClient{idx}]\ntype\t\t\t=\ttcp\nport\t\t\t=\t{port}\n"
            "address\t\t\t=\t127.0.0.1\nso_sndbuf\t\t=\t65536\nso_rcvbuf\t\t=\t65536\n"
            "ibuffermax\t\t=\t1048576\nobuffermax\t\t=\t1048576\ntcp_nodelay\t\t=\t1\n"
            "listen_backlog\t=\t10\naccumulate\t\t=\t104857600\n\n"
        )
    for k in ["GamedbClient", "LogclientClient", "LogclientTcpClient", "ThreadPool"]:
        if k in fixed:
            gm_out += fixed[k] + "\n\n"
    await write_conf_atomic(path, gm_out.rstrip() + "\n")


async def _rebuild_start_sh(glinkd_count: int) -> None:
    path = Path("/home/start.sh")
    if not path.exists():
        return
    lines = path.read_text().splitlines(keepends=True)
    new_lines = []
    insert_pos = None
    for line in lines:
        if re.search(r'\./glinkd gamesys\.conf \d+', line):
            if insert_pos is None:
                insert_pos = len(new_lines)
        else:
            new_lines.append(line)
    if insert_pos is None:
        insert_pos = len(new_lines)
    insert = []
    for n in range(1, glinkd_count + 1):
        log = "glink.log" if n == 1 else f"glink{n}.log"
        insert.append(f"cd $PW_PATH/glinkd; ./glinkd gamesys.conf {n} >$PW_PATH/logs/{log} 2>&1 &\n")
    new_lines[insert_pos:insert_pos] = insert
    await write_conf_atomic(path, "".join(new_lines))
