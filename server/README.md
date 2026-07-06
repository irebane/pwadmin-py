# Server-side files

Everything in this directory is meant to be deployed *to* the game/app server, as opposed
to `app/`, `templates/`, `static/` etc. which are pwadmin-py's own application code. See
[DEPLOY.md](../DEPLOY.md) for the full install walkthrough — this is a map of what lives
here and why.

| Path | Deployed to | Purpose |
|---|---|---|
| [pwadmin.service](pwadmin.service) | `/etc/systemd/system/pwadmin.service` | systemd unit that runs the pwadmin-py app itself |
| [gs_zone.sh](gs_zone.sh) | `$SERVER_PATH/gs_zone.sh` (e.g. `/home/gs_zone.sh`) | Per-zone start/stop helper — invoked directly by `app/routers/server.py` and `app/services/instance_watch.py` via `sudo`. The app will not be able to start/stop individual zone processes without this in place |
| [patches/](patches/) | Various, see [patches/README.md](patches/README.md) | LD_PRELOAD binary patches that hot-fix dead/buggy code in the stock `gs` binaries, plus the `restart2` crash-recovery script fix |
| [pwserver.service](pwserver.service) | `/etc/systemd/system/pwserver.service` | systemd unit for the PW game server itself — `ExecStart=start.sh`, `ExecStop=stop.sh` |
| [start.sh](start.sh) | `$SERVER_PATH/start.sh` (e.g. `/home/start.sh`) | Launches every game-server daemon in order (`logservice`, `uniquenamed`, `authd`, `gamedbd`, `gacd`, `gfactiond`, `gdeliveryd`, `glinkd` x2, then `gs`). **This is where `LD_PRELOAD` for the patches in `patches/` actually gets set** on the main `gs01` process — see the `pw_expfix_1.5.5`/`pw_instance_watch_1.5.5` READMEs |
| [stop.sh](stop.sh) | `$SERVER_PATH/stop.sh` (e.g. `/home/stop.sh`) | Graceful-then-forceful shutdown of every daemon `start.sh` launches, in reverse dependency order |

**Note:** `restart2` (under `patches/restart2_selfheal_fix/`) is `gs`'s own internal
crash-recovery script — a *third*, separate `LD_PRELOAD` site distinct from `start.sh`.
It currently only sets `LD_PRELOAD=./pw_expfix_155.so`, missing `pw_instance_watch.so` —
see [patches/restart2_selfheal_fix/README.md](patches/restart2_selfheal_fix/README.md).

## Why these are grouped separately from `app/`

Everything here runs as (or is invoked by) processes on the game server's OS directly —
systemd units, shell scripts, compiled `.so`/binary patches — rather than being imported
by or running inside the FastAPI app process. Keeping them in one directory makes it
obvious at a glance what needs to be copied onto a server and kept in sync, versus what's
just `git pull`ed and picked up automatically by the running app (see
[DEPLOY.md](../DEPLOY.md#deploy-updates)).
