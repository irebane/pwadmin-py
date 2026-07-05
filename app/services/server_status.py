import asyncio
import socket
import struct
from pathlib import Path
from app.config import settings

# Live player-count read, verified 2026-07-05 via disassembly of /home/gamed/gs (non-PIE, so
# these addresses/offsets are fixed and identical across every gs <zone> process):
# world_manager::GetInstance() is `mov eax, [WORLD_MANAGER_PTR_ADDR]; ret` — a fixed-address
# global singleton pointer. world_manager::AllocPlayer()/FreePlayer() both compute
# `this + 0xC0` as the obj_manager<gplayer> member, and
# obj_manager_basic<gplayer>::GetAllocedCount() reads `*(member + 0x10)`, with Alloc()/Free()
# doing incl/decl on exactly that field — a genuine live "currently connected" counter, not a
# capacity/pool-size value. See docs/zone-lifecycle-and-gm-protocol.md for the full derivation.
WORLD_MANAGER_PTR_ADDR = 0x094C2BFC
PLAYER_COUNT_OFFSET = 0xD0


def read_zone_player_count(pid: int) -> int | None:
    """Passive read of the live player count directly out of a running gs <zone> process's
    own memory (two 4-byte reads via /proc/<pid>/mem). Cannot affect the target process.
    Returns None if the read fails for any reason — callers must treat that as "unknown", not
    "empty"."""
    try:
        with open(f"/proc/{pid}/mem", "rb", buffering=0) as f:
            f.seek(WORLD_MANAGER_PTR_ADDR)
            world_manager_ptr = struct.unpack("<I", f.read(4))[0]
            if world_manager_ptr == 0:
                return None
            f.seek(world_manager_ptr + PLAYER_COUNT_OFFSET)
            count = struct.unpack("<i", f.read(4))[0]
            return count if count >= 0 else None  # sanity check — a real count is never negative
    except Exception:
        return None

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

    cpu_pct = 0
    try:
        s1 = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        await asyncio.sleep(0.2)
        s2 = Path("/proc/stat").read_text().splitlines()[0].split()[1:]
        idle1, idle2 = int(s1[3]), int(s2[3])
        total1 = sum(int(x) for x in s1)
        total2 = sum(int(x) for x in s2)
        dt = total2 - total1
        cpu_pct = round((1 - (idle2 - idle1) / dt) * 100) if dt else 0
    except Exception:
        pass

    return {
        "cpu_pct": cpu_pct,
        "mem_total": mem_total,
        "mem_used": mem_used,
        "mem_free": mem_free,
        "services": services,
        "glinkd": glinkd,
    }


def get_running_zone_pids() -> dict[str, int]:
    """Scan /proc for live `./gs <zone>` processes, zone_id -> pid. Shared by maps status and
    instance_watch (which also needs the pid to read live player counts from process memory)."""
    import glob, re
    running: dict[str, int] = {}
    for cmdfile in glob.glob("/proc/[0-9]*/cmdline"):
        try:
            cmd = open(cmdfile, "rb").read().replace(b"\x00", b" ").decode(errors="replace").strip()
            m = re.match(r'\./gs\s+(\S+)', cmd)
            if m:
                pid = int(cmdfile.split("/")[2])
                running[m.group(1)] = pid
        except Exception:
            continue
    return running


def get_running_zone_ids() -> set[str]:
    return set(get_running_zone_pids().keys())


async def get_maps_status() -> dict:
    zones = settings.gs_zones_dict
    online, offline = [], []
    running_pids = get_running_zone_pids()
    for zone_id, info in zones.items():
        name = info.get("name", zone_id) if isinstance(info, dict) else info
        ztype = info.get("type", "") if isinstance(info, dict) else ""
        pid = running_pids.get(zone_id)
        if pid is not None:
            entry = {"id": zone_id, "name": name, "type": ztype, "players": read_zone_player_count(pid)}
            online.append(entry)
        else:
            offline.append({"id": zone_id, "name": name, "type": ztype})
    return {"online": online, "offline": offline}
