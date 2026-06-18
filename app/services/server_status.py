import asyncio
from pathlib import Path

SERVER_DAEMON_NAMES = [
    "logservice", "uniquenamed", "gdelivery", "gamedbd",
    "gamed", "glinkd", "factiond", "csstatus", "gbridge",
]


async def get_daemon_status() -> list[dict]:
    """Check which server daemons are running."""
    result = []
    for daemon in SERVER_DAEMON_NAMES:
        try:
            proc = await asyncio.create_subprocess_exec(
                "pgrep", "-x", daemon,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=2.0)
            running = bool(stdout.strip())
        except (asyncio.TimeoutError, FileNotFoundError):
            running = False
        result.append({"name": daemon, "running": running})
    return result


async def get_ram_usage() -> dict:
    """Read /proc/meminfo for RAM stats (Linux only)."""
    try:
        meminfo = Path("/proc/meminfo").read_text()

        def parse_kb(key: str) -> int:
            for line in meminfo.splitlines():
                if line.startswith(key):
                    return int(line.split()[1])
            return 0

        total = parse_kb("MemTotal:")
        free = parse_kb("MemFree:")
        return {"total_kb": total, "free_kb": free, "used_kb": total - free}
    except FileNotFoundError:
        return {"total_kb": 0, "free_kb": 0, "used_kb": 0}
