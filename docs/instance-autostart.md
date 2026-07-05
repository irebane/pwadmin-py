# Instance Autostart / Auto-Stop

Reference for the on-demand zone lifecycle feature added to pwadmin-py. For the full
investigation history (dead ends included), see
[`zone-lifecycle-and-gm-protocol.md`](zone-lifecycle-and-gm-protocol.md) — this document is
the clean "how it actually works" summary of where that investigation landed.

## What it does

Two independent toggles, both on the Server page's Map Management card:

- **Auto-Start** — when a player tries to enter or log into a zone that's currently offline,
  starts it automatically (`gs_zone.sh start <zone>`), instead of the player just getting
  "Can't Enter Instance" / "Couldn't login to server" with no recovery.
- **Auto-Stop** — stops a zone (`gs_zone.sh stop <zone>`) after it's had zero players for a
  configurable idle timeout. `gs01` (the main world) and any zone marked `"type": "world"` in
  `GS_ZONES` are always exempt.

Both are off by default (opt-in) and persist across restarts in `data/autostart_state.json`.

## Auto-Start: two trigger sources

The PW 1.5.5 binaries have no client-facing "player wants zone X" signal on their own, so this
uses two different mechanisms depending on how the request happens:

1. **Voluntary zone switch** (portal, teleport item) — an LD_PRELOAD hook
   (`patches/pw_instance_watch_1.5.5/pw_instance_watch.c`) sits on
   `world_manager::PlaneSwitch(...)` inside `gs01` and logs every call to
   `/tmp/pw_switch_watch.log`. `app/services/instance_watch.py`'s `_tail_hook_log()` tails that
   file and resolves the logged `worldtag` to a `zone_id` via `gs.conf`'s `tag = N` lines.

2. **Login / character resume** — confirmed by direct testing that `PlaneSwitch` does **not**
   fire when a character is placed into their last saved position at login. Solved without
   touching the binary: `_tail_login_log()` tails `authd`'s plaintext log for
   `UserLogin:userid=N` lines, and for each one queries `gamedbd` directly
   (`GameClient.get_user_roles()`, port 29400) for that account's characters' saved
   `world_tag`. A one-shot sweep over every account in the `users` table also runs once when
   the watcher starts, so a zone comes back proactively rather than only on the next failed
   login attempt.

Both paths converge on `_maybe_autostart()`, which has a 30s per-zone cooldown so repeated
retries (a player mashing a portal, or several failed login attempts) don't fire redundant
starts.

## Auto-Stop: real occupancy, not a proxy signal

**This went through two designs before landing on something correct — worth knowing if you
touch this code.**

- *First attempt*: an idle timer keyed off the same "someone requested this zone" activity
  used by auto-start. Problem: that only tells you someone *asked* to enter recently, not that
  they're still there. A zone with a player who's been inside for an hour without a fresh
  request would still get stopped.
- *Second attempt*: cross-reference MySQL's `online` table (who's connected right now) against
  `GameClient.get_user_roles()`'s `world_tag`/position field per online account, on the theory
  that gamedbd keeps that live. **Wrong** — that field is frozen at whatever it was at last
  login/checkpoint, not updated by in-session zone switches. Confirmed live: an account showed
  `map=1` (the main world) while their character was demonstrably active inside a different
  zone at that exact moment (continuous real hook traffic for that zone). Deployed briefly,
  and it stopped a zone a real player was still connected to — the exact failure mode it was
  supposed to prevent.
- *What actually works*: read the live player count directly out of the zone's own process
  memory. No hooking, no protocol assumptions — just two passive reads.

### The memory read

Found by disassembling `/home/gamed/gs` (unstripped, full debug symbols, and — critically —
`readelf -h` shows `Type: EXEC` not `DYN`, i.e. no PIE/ASLR, so every global address below is
identical across *every* `gs <zone>` process, not just one):

```
world_manager::GetInstance():
    mov eax, [0x094C2BFC]      ; global singleton pointer, fixed address
    ret

world_manager::AllocPlayer() / FreePlayer(gplayer*):
    both compute `this + 0xC0`  ; the obj_manager<gplayer> member

obj_manager_basic<gplayer>::GetAllocedCount() const:
    mov eax, [this]
    mov eax, [eax + 0x10]       ; the actual counter
    ret

obj_manager_basic<gplayer>::Alloc() / Free(gplayer*):
    `incl 0x10(%eax)` / `decl 0x10(%eax)`   ; confirms it's live, not a pool-size constant
```

So: `player_count = *(int*)(*(int*)0x094C2BFC + 0xD0)`, implemented as
`app/services/server_status.py::read_zone_player_count(pid)` — two `seek`+`read(4)` calls via
`/proc/<pid>/mem`. Purely a read; cannot affect the target process. Returns `None` on any
failure (process gone, unexpected layout) rather than guessing — callers must treat `None` as
"unknown", not "empty", and fall back to the request-based idle timer for that check.

Verified live: `gs01` read `player_count=3`, matching exactly the 3 currently-online accounts
with valid characters (out of 4 online — the 4th had no character data and correctly wasn't
counted).

`_idle_check_loop()` in `instance_watch.py` runs every 60s, and for every running,
stop-eligible zone: reads the live count; if `>0`, refreshes its activity timestamp and skips
it unconditionally; if `0` (or the read failed), falls through to the idle-timer check as
before.

## Known limitations

- The live player-count read depends on the exact binary layout found by disassembly on
  2026-07-05. If the `gs` binary is ever rebuilt/patched/upgraded, these offsets could
  silently become wrong — there's no runtime cross-check beyond the sanity check that the
  count is non-negative. Worth re-verifying (`server_status.read_zone_player_count` against a
  zone with a known player count) after any binary change.
- Idle-check granularity is 60s, so a zone can take up to `idle_minutes + 1m` to actually stop
  after hitting 0 players.
- Zone *starting* still takes roughly 30-60s from request to actually being enterable — that's
  the zone process's own provider-registration handshake with `gdeliveryd` (a compiled-in
  retry/backoff timer in the game binary's own networking code), not something pwadmin-py
  controls. The 30s cooldown on repeated auto-start triggers is sized around this.

## Files

| File | Role |
|---|---|
| `app/services/instance_watch.py` | Watcher: both auto-start trigger tails, the idle-check loop, state persistence |
| `app/services/server_status.py` | `get_running_zone_pids()`, `read_zone_player_count()` — shared with the plain map-status endpoint too |
| `app/services/game_client.py` | Binary protocol client to gamedbd (port 29400), used for the login-resume trigger |
| `patches/pw_instance_watch_1.5.5/pw_instance_watch.c` | LD_PRELOAD hook on `PlaneSwitch`, loaded into `gs01` only |
| `app/routers/server.py` | `/api/server/autostart` (get/set), manual-action logging into the same Instance Activity log |
| `templates/server/index.html` | UI: toggles + tooltips in Map Management, Instance Activity log card |
