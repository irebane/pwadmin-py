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

## Why these are grouped separately from `app/`

Everything here runs as (or is invoked by) processes on the game server's OS directly —
systemd units, shell scripts, compiled `.so`/binary patches — rather than being imported
by or running inside the FastAPI app process. Keeping them in one directory makes it
obvious at a glance what needs to be copied onto a server and kept in sync, versus what's
just `git pull`ed and picked up automatically by the running app (see
[DEPLOY.md](../DEPLOY.md#deploy-updates)).
