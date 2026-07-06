# pwadmin-py

A FastAPI-based web admin panel for Perfect World private servers (PWI 1.4.2 / 1.5.5) —
account management, item builder, G-Shop editing, server control, and instance
autostart/auto-stop, all talking directly to the game server's own MySQL database and
binary protocols instead of shelling out to the stock game tools.

## Status

Actively developed, changes daily. Documented on a best-effort basis via commit messages
and the `.md` files under [docs/](docs/), but things may be incomplete or break between
commits. A lot of the game-server-internals knowledge here (see
[docs/zone-lifecycle-and-gm-protocol.md](docs/zone-lifecycle-and-gm-protocol.md)) comes
from direct reverse-engineering and observation, not official documentation — some of it
may be wrong. Not yet hardened for exposure beyond a trusted/local network; see
[Security](#security) below.

Feedback, bug reports, and feature requests are welcome — open an issue.

## Features

- Account management: search/list/edit accounts, characters, GM rank, bans, gold grants
- Item Builder: browse the item database, build custom items, send via in-game mail
- G-Shop editor
- Server Config: edit `ptemplate.conf`/`gamesys.conf` values, per-daemon status
- Instance Autostart/Auto-Stop: starts zones on demand instead of running everything
  24/7 (see [docs/instance-autostart.md](docs/instance-autostart.md))
- LD_PRELOAD binary patches for stock `gs` binaries with dead/buggy rate-bonus code (see
  [server/patches/](server/patches/))

## Known gaps

- Gold shop editing (price/items) mostly works on 1.4.2 but is currently broken on 1.5.5
  — not an immediate priority given 1.5.5's stock gameshop is already reasonably good.

## Security

This has not been audited for exposure to an untrusted network — treat it as suitable for
a trusted LAN/family-server setup, not a public-facing production deployment, until
stated otherwise. If you find an access-control or injection issue, please open an issue
or reach out directly rather than exploiting it.

## Requirements

- Python 3.11+
- MySQL / MariaDB
- A Linux server with systemd (the game server itself; pwadmin-py's app server can run
  elsewhere)

## Deployment

See [DEPLOY.md](DEPLOY.md) for the full walkthrough (install, `.env` configuration,
systemd service, sudoers permissions). Short version:

```bash
git clone https://github.com/irebane/pwadmin-py.git
cd pwadmin-py
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # fill in your DB/server values
sudo cp server/pwadmin.service /etc/systemd/system/
sudo systemctl enable --now pwadmin
```

Everything under [server/](server/) — the systemd unit, the game-server launch scripts,
and the binary patches — is meant to be copied onto the server itself; see
[server/README.md](server/README.md) for what each file does.

## Credits / Inspiration

Not built from scratch in a vacuum — a lot of the feature set here (item builder, account
tools, G-Shop editing) follows the shape of earlier community PW admin panels. Where
something was directly adapted rather than just inspired by, it's noted at the point of
use (e.g. [scripts/convert_items.php](scripts/convert_items.php)).

- [shadowvzs/pwAdmin](https://github.com/shadowvzs/pwAdmin) — PHP/JS/CSS admin panel for
  PWI 1.4.2 (item builder, webshop, account manager). `scripts/convert_items.php` reads
  this project's `php/pw_items.php` item database as one of its two supported sources.
- [hrace009/pwAdmin](https://github.com/hrace009/pwAdmin) — JSP/Java admin panel using the
  PW-Java API. The JSP-based admin tool historically deployed alongside these servers
  (`webapps/pwadmin/`) is this same lineage.
- **iWeb** — a bundled Tomcat webapp (`webapps/iweb/`, `iwebservice.jar`) shipped
  alongside the JSP admin tool above in the original server packs this project targets,
  providing an account auto-lock protocol (`IWebAutolockSet`/`IWebAutolockGet`). Appears
  to be part of the original commercial Perfect World server distribution rather than a
  separately maintained open-source project — no standalone repository found to credit
  beyond the JSP tool it ships with.

Neither `pwAdmin` repo above lists an explicit license. If you're the author of either
project and want specific attribution wording changed, open an issue.
