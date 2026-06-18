import asyncio
import socket
from pathlib import Path
from app.config import settings

SERVICES = [
    ("logservice",  "Log Service"),
    ("uniquenamed", "Unique Name Daemon"),
    ("authd",       "Auth Daemon"),
    ("gamedbd",     "Game DB Daemon"),
    ("gacd",        "Anti-Cheat Daemon"),
    ("gfactiond",   "Faction Daemon"),
    ("gdeliveryd",  "Delivery Daemon"),
    ("glinkd",      "Game Link Daemon"),
    ("gs",          "Map Service"),
]


async def _pgrep_count(process: str) -> int:
    try:
        proc = await asyncio.create_subprocess_exec(
            "pgrep", "-cx", process,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
        return int(stdout.strip()) if stdout.strip() else 0
    except Exception:
        return 0


def _check_port(host: str, port: int) -> bool:
    try:
        s = socket.socket()
        s.settimeout(0.2)
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def _read_glinkd_count() -> int:
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


async def get_server_status() -> dict:
    counts = await asyncio.gather(*[_pgrep_count(p) for p, _ in SERVICES])

    services = [
        {"label": label, "process": proc, "count": cnt, "running": cnt > 0}
        for (proc, label), cnt in zip(SERVICES, counts)
    ]

    glinkd_count = _read_glinkd_count()
    glinkd = []
    for n in range(1, glinkd_count + 1):
        client_port = 29000 + (n - 1)
        zone_port = 29300 + n
        glinkd.append({
            "instance": n,
            "client_port": client_port,
            "zone_port": zone_port,
            "up": _check_port(settings.lan_ip, client_port),
        })

    mem_total = mem_used = mem_free = 0
    try:
        meminfo = Path("/proc/meminfo").read_text()

        def pkb(key: str) -> int:
            for line in meminfo.splitlines():
                if line.startswith(key):
                    return round(int(line.split()[1]) / 1024)
            return 0

        mem_total = pkb("MemTotal:")
        mem_free = pkb("MemAvailable:")
        mem_used = mem_total - mem_free
    except Exception:
        pass

    return {
        "mem_total": mem_total,
        "mem_used": mem_used,
        "mem_free": mem_free,
        "services": services,
        "glinkd": glinkd,
    }


async def get_maps_status() -> dict:
    zones = settings.gs_zones_dict
    online, offline = [], []
    try:
        import glob
        for zone_id, info in zones.items():
            name = info.get("name", zone_id) if isinstance(info, dict) else info
            running = False
            for cmdfile in glob.glob("/proc/[0-9]*/cmdline"):
                try:
                    cmd = open(cmdfile, "rb").read().replace(b"\x00", b" ").decode(errors="replace")
                    if f"./gs {zone_id}" in cmd:
                        running = True
                        break
                except Exception:
                    continue
            entry = {"id": zone_id, "name": name}
            (online if running else offline).append(entry)
    except Exception:
        pass
    return {"online": online, "offline": offline}
