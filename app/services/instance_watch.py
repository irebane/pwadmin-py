"""
Autostart/auto-stop watcher for on-demand zone lifecycle management.

Two independent trigger sources feed the same autostart logic:

1. Voluntary in-game zone switches (portal/teleport item). PW 1.5.5's binaries have no
   client-facing signal for this other than the internal call
   world_manager::PlaneSwitch(...). An LD_PRELOAD hook (patches/pw_instance_watch_1.5.5) is
   loaded into gs01 and appends one line per call to /tmp/pw_switch_watch.log, e.g.:

       1783230200.685616763 [PlaneSwitch] this=... player=... pos=... worldtag=102 ikey_ptr=... flag=0 ikey_bytes=...

   _tail_hook_log() tails that file and resolves worldtag -> zone_id via gs.conf's
   `tag = N` lines (see _build_tag_zone_map).

2. Login / character resume. Confirmed by direct testing (2026-07-05) that PlaneSwitch does
   NOT fire when a character is placed into their last saved position at login — a stuck
   character whose saved zone is offline gets "Couldn't login to server" with zero hook
   activity, and no automatic recovery. Rather than reverse-engineer the actual login/resume
   placement function in the gs01 binary, this is solved without touching the binary at all:
   _tail_login_log() tails authd's plaintext log for `UserLogin:userid=N` lines, and for each
   one queries gamedbd directly (GameClient.get_user_roles(), the same read-only protocol
   pwadmin-py's account pages already use) to get that account's characters' saved world_tag,
   and ensures each such zone is running. A proactive sweep over every known account also runs
   once when the watcher starts, so a zone comes back up even before anyone attempts to log in
   after e.g. a `pwserver` restart.

Both paths funnel into _maybe_autostart(), which calls /home/gs_zone.sh start <zone> if the
resolved zone isn't already running (with a per-zone cooldown to dedup retries). Last-seen-
activity per zone is also tracked here for the idle auto-stop side, if enabled.

Caveat: neither trigger reflects ongoing presence, only "someone just tried to get into this
zone". "Idle" means "no one has switched into or logged into this zone recently" — a zone with
players who never leave and never re-trigger either signal could still look idle. There is
currently no cheaper signal available for live per-zone player counts. Full details in
docs/zone-lifecycle-and-gm-protocol.md.

Runs as background asyncio tasks inside the pwadmin-py process itself (it already runs
directly on the game server, see server_status.py / server_config.py for the same
local-filesystem-access pattern).
"""
import asyncio
import json
import re
import time
from pathlib import Path

from app.config import settings
from app.services.server_status import get_running_zone_ids
from app.services.game_client import GameClient

HOOK_LOG_PATH = Path("/tmp/pw_switch_watch.log")
AUTHD_LOG_PATH = Path(settings.server_path) / "logs" / "authd.log"
_STATE_FILE = Path(__file__).parent.parent.parent / "data" / "autostart_state.json"
_ACTIVITY_FILE = Path(__file__).parent.parent.parent / "data" / "instance_watch_log.json"

START_COOLDOWN_SECONDS = 30      # per-zone dedup: don't re-trigger gs_zone.sh start on retries
IDLE_CHECK_INTERVAL_SECONDS = 300
TAIL_POLL_INTERVAL_SECONDS = 1.5
MAX_LOG_ENTRIES = 300
DEFAULT_IDLE_MINUTES = 60
PROTECTED_ZONES = {"gs01"}        # never touched: core world, not managed by gs_zone.sh

_LINE_RE = re.compile(r"worldtag=(\d+)")
_LOGIN_RE = re.compile(r"UserLogin:userid=(\d+)")

# module-level runtime state — single process, single watcher instance
_tag_zone: dict[int, str] = {}
_last_activity: dict[str, float] = {}
_last_start_attempt: dict[str, float] = {}
_log_entries: list[dict] = []
_tasks: list[asyncio.Task] = []
_pending_tasks: set[asyncio.Task] = set()  # strong refs for fire-and-forget spawns; see _spawn()
_offset = 0
_login_offset = 0


def _spawn(coro) -> None:
    """asyncio.create_task() only holds a *weak* reference — with nothing else referencing
    the task, it can be garbage-collected before it ever runs (silently, no error). Keep a
    strong reference until it completes."""
    task = asyncio.create_task(coro)
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)


def _read_state() -> dict:
    try:
        return json.loads(_STATE_FILE.read_text()) if _STATE_FILE.exists() else {}
    except Exception:
        return {}


def _write_state(state: dict) -> None:
    _STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state))


def is_enabled() -> bool:
    return bool(_read_state().get("enabled", False))


def get_idle_minutes() -> int:
    return int(_read_state().get("idle_minutes", DEFAULT_IDLE_MINUTES))


def get_log() -> list[dict]:
    return _log_entries


def _load_log() -> None:
    global _log_entries
    try:
        _log_entries = json.loads(_ACTIVITY_FILE.read_text()) if _ACTIVITY_FILE.exists() else []
    except Exception:
        _log_entries = []


def _persist_log() -> None:
    try:
        _ACTIVITY_FILE.parent.mkdir(parents=True, exist_ok=True)
        _ACTIVITY_FILE.write_text(json.dumps(_log_entries))
    except Exception:
        pass


def _log(text: str) -> None:
    _log_entries.insert(0, {"ts": time.time(), "text": text})
    if len(_log_entries) > MAX_LOG_ENTRIES:
        del _log_entries[MAX_LOG_ENTRIES:]
    _persist_log()


def _build_tag_zone_map() -> dict[int, str]:
    """Parse gs.conf's [World_x]/[Instance_x] sections for their `tag = N` value.

    Zone ids are matched against settings.gs_zones_dict so unmanaged/unused sections in
    gs.conf (e.g. a stray duplicate [World_gs02__]) are ignored automatically.
    """
    path = Path(settings.server_path) / "gamed" / "gs.conf"
    zones = settings.gs_zones_dict
    tag_map: dict[int, str] = {}
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return tag_map

    header_re = re.compile(r"^\[(?:World|Instance)_([A-Za-z0-9]+)")
    tag_re = re.compile(r"^tag\s*=\s*(\d+)", re.IGNORECASE)
    current_zone = None
    for raw in content.splitlines():
        line = raw.strip()
        if line.startswith("["):
            m = header_re.match(line)
            current_zone = m.group(1) if m else None
            continue
        if current_zone is None:
            continue
        m2 = tag_re.match(line)
        if m2:
            tag = int(m2.group(1))
            if current_zone in zones and tag not in tag_map:
                tag_map[tag] = current_zone
            current_zone = None  # only the first tag= line per section counts
    return tag_map


async def _autostart_zone(zone_id: str, name: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "/home/gs_zone.sh", "start", zone_id,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode(errors="replace").strip()
        if "Started" in output:
            _log(f"Auto-started {zone_id} ({name}) — requested by player")
        elif "Already running" in output:
            pass  # race: came up between our running-check and this call
        elif "Insufficient memory" in output:
            _log(f"Auto-start FAILED for {zone_id} ({name}): {output}")
        else:
            _log(f"Auto-start {zone_id} ({name}): {output or 'unknown result'}")
    except Exception as e:
        _log(f"Auto-start ERROR for {zone_id} ({name}): {e}")


async def _autostop_zone(zone_id: str, name: str) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            "sudo", "/home/gs_zone.sh", "stop", zone_id,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT,
        )
        stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=15)
        output = stdout.decode(errors="replace").strip()
        _last_activity.pop(zone_id, None)
        _log(f"Auto-stopped {zone_id} ({name}) — idle {get_idle_minutes()}+ min ({output or 'stopped'})")
    except Exception as e:
        _log(f"Auto-stop ERROR for {zone_id} ({name}): {e}")


def _maybe_autostart(zone_id: str | None) -> None:
    """Shared by both trigger sources: bump activity, start the zone if it's offline."""
    if not zone_id or zone_id in PROTECTED_ZONES:
        return

    now = time.time()
    _last_activity[zone_id] = now

    if zone_id in get_running_zone_ids():
        return

    last_attempt = _last_start_attempt.get(zone_id, 0)
    if now - last_attempt < START_COOLDOWN_SECONDS:
        return
    _last_start_attempt[zone_id] = now

    name = settings.gs_zones_dict.get(zone_id, {}).get("name", zone_id)
    _spawn(_autostart_zone(zone_id, name))


async def _handle_line(line: str) -> None:
    m = _LINE_RE.search(line)
    if not m:
        return
    tag = int(m.group(1))
    _maybe_autostart(_tag_zone.get(tag))


async def _ensure_user_zones_started(user_id: int) -> None:
    """Query gamedbd directly for this account's characters' saved world_tag and make sure
    each one's zone is running — covers login/character-resume, which does not go through
    the PlaneSwitch hook at all (confirmed by direct testing)."""
    try:
        client = GameClient(host="localhost", port=settings.server_port)
        roles = await client.get_user_roles(user_id)
    except Exception as e:
        _log_error_throttled("gamedbd query", e)
        return
    for role in roles:
        _maybe_autostart(_tag_zone.get(role.get("map")))


async def _sweep_all_accounts() -> None:
    """One-shot proactive sweep over every known account, run once when the watcher starts.
    Covers the case where a zone died (crash, restart, manual stop) and nobody has attempted
    to log in yet — without this, the fix is purely reactive to a login attempt."""
    try:
        from sqlalchemy import text
        from app.database import engine
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT id FROM users"))
            user_ids = [row[0] for row in result.fetchall()]
    except Exception as e:
        _log_error_throttled("account sweep", e)
        return
    for uid in user_ids:
        await _ensure_user_zones_started(uid)


_last_error_logged: dict[str, float] = {}


def _log_error_throttled(loop_name: str, exc: Exception) -> None:
    """Tail loops run every 1.5s — never let a persistent error flood the activity log."""
    now = time.time()
    if now - _last_error_logged.get(loop_name, 0) >= 30:
        _last_error_logged[loop_name] = now
        _log(f"{loop_name} ERROR: {exc!r}")


async def _tail_hook_log() -> None:
    global _offset
    while True:
        try:
            if HOOK_LOG_PATH.exists():
                size = HOOK_LOG_PATH.stat().st_size
                if size < _offset:
                    _offset = 0  # file was rotated (truncated) since our last read
                if size > _offset:
                    with open(HOOK_LOG_PATH, "r", errors="replace") as f:
                        f.seek(_offset)
                        chunk = f.read()
                        _offset = f.tell()
                    for line in chunk.splitlines():
                        await _handle_line(line)
            else:
                _offset = 0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log_error_throttled("hook-log tail", e)
        await asyncio.sleep(TAIL_POLL_INTERVAL_SECONDS)


async def _tail_login_log() -> None:
    global _login_offset
    while True:
        try:
            with open("/tmp/login_tail_debug.log", "a") as dbgf:
                dbgf.write(f"{time.time()} offset={_login_offset} exists={AUTHD_LOG_PATH.exists()} "
                           f"size={AUTHD_LOG_PATH.stat().st_size if AUTHD_LOG_PATH.exists() else 'n/a'}\n")
            if AUTHD_LOG_PATH.exists():
                size = AUTHD_LOG_PATH.stat().st_size
                if size < _login_offset:
                    _login_offset = 0
                if size > _login_offset:
                    with open(AUTHD_LOG_PATH, "r", errors="replace") as f:
                        f.seek(_login_offset)
                        chunk = f.read()
                        _login_offset = f.tell()
                    for line in chunk.splitlines():
                        m = _LOGIN_RE.search(line)
                        if m:
                            _spawn(_ensure_user_zones_started(int(m.group(1))))
            else:
                _login_offset = 0
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log_error_throttled("login-log tail", e)
        await asyncio.sleep(TAIL_POLL_INTERVAL_SECONDS)


async def _idle_check_loop() -> None:
    while True:
        await asyncio.sleep(IDLE_CHECK_INTERVAL_SECONDS)
        try:
            idle_seconds = get_idle_minutes() * 60
            now = time.time()
            zones = settings.gs_zones_dict
            for zone_id in get_running_zone_ids():
                if zone_id in PROTECTED_ZONES:
                    continue
                info = zones.get(zone_id)
                # "world"-type zones are protected the same way "Stop Maps (Keep World)" protects them
                if not info or info.get("type") == "world":
                    continue
                last = _last_activity.get(zone_id)
                if last is None:
                    # no observed entry event yet since the watcher started — seed a baseline
                    # now instead of stopping immediately on zero data
                    _last_activity[zone_id] = now
                    continue
                if now - last >= idle_seconds:
                    await _autostop_zone(zone_id, info.get("name", zone_id))
        except asyncio.CancelledError:
            raise
        except Exception as e:
            _log_error_throttled("idle-check", e)


def _reset_runtime_state() -> None:
    global _offset, _login_offset
    _tag_zone.clear()
    _tag_zone.update(_build_tag_zone_map())
    _last_activity.clear()
    _last_start_attempt.clear()
    _offset = HOOK_LOG_PATH.stat().st_size if HOOK_LOG_PATH.exists() else 0
    _login_offset = AUTHD_LOG_PATH.stat().st_size if AUTHD_LOG_PATH.exists() else 0


def start() -> None:
    global _tasks
    if _tasks:
        return
    _reset_runtime_state()
    _tasks = [
        asyncio.create_task(_tail_hook_log()),
        asyncio.create_task(_tail_login_log()),
        asyncio.create_task(_idle_check_loop()),
    ]
    _log(f"Autostart watcher enabled — tracking {len(_tag_zone)} zone(s), idle timeout {get_idle_minutes()}m")
    _spawn(_sweep_all_accounts())


def stop() -> None:
    global _tasks
    for t in _tasks:
        t.cancel()
    if _tasks:
        _log("Autostart watcher disabled")
    _tasks = []


def set_enabled(enabled: bool, idle_minutes: int | None = None) -> None:
    state = _read_state()
    state["enabled"] = enabled
    if idle_minutes is not None:
        state["idle_minutes"] = max(5, int(idle_minutes))
    _write_state(state)
    if enabled:
        start()
    else:
        stop()


def init_on_startup() -> None:
    _load_log()
    if is_enabled():
        start()


def shutdown() -> None:
    stop()
