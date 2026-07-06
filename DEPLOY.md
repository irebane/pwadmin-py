# Deployment Guide

## Requirements

- Python 3.11+
- MySQL / MariaDB
- A Linux server with systemd
- `git` installed on the server

## Install

```bash
# Clone the repo
git clone https://github.com/irebane/pwadmin-py.git /path/to/pwadmin-py
cd /path/to/pwadmin-py

# Create virtualenv and install dependencies
python3 -m venv venv
venv/bin/pip install --upgrade pip
venv/bin/pip install -r requirements.txt
```

## Configuration

Copy the example env file and fill in your values:

```bash
cp .env.example .env
nano .env
```

| Variable | Description |
|---|---|
| `DB_HOST` | MySQL host (usually `localhost`) |
| `DB_USER` | MySQL user |
| `DB_PASSWORD` | MySQL password |
| `DB_NAME` | Database name |
| `SERVER_PATH` | Absolute path to the game server root (e.g. `/home`) |
| `SERVER_IP` | Game server IP |
| `SECRET_KEY` | Random secret for session signing — generate with `openssl rand -hex 32` |
| `ADMIN_ID` | Admin account character ID |
| `ADMIN_PW` | Admin password hash (see PHP app or generate with the provided script) |
| `PW_CLASSES` | JSON map of class IDs to display names |
| `GS_ZONES` | JSON map of zone IDs to `{name, type}` |
| `SERVER_FILES` | JSON map of server component IDs to `folder*daemon` paths |

## Run as a systemd service

A service file is included at `server/pwadmin.service`. Adjust `User`, `WorkingDirectory`, and `ExecStart` paths to match your setup, then install it:

```bash
sudo cp server/pwadmin.service /etc/systemd/system/pwadmin.service
sudo systemctl daemon-reload
sudo systemctl enable pwadmin
sudo systemctl start pwadmin
```

Check status and logs:

```bash
sudo systemctl status pwadmin
sudo journalctl -u pwadmin -f
```

### Per-zone start/stop script

Instance Autostart (`app/services/instance_watch.py`) and the manual zone controls on
the Server Config page (`app/routers/server.py`) both shell out to `sudo /home/gs_zone.sh
start|stop <zone>` — the app will not be able to start/stop individual zone processes
without this script in place. Copy it to the game server root (`SERVER_PATH` in `.env`,
typically `/home`) and make it executable:

```bash
sudo cp server/gs_zone.sh /home/gs_zone.sh
sudo chmod 755 /home/gs_zone.sh
```

It assumes `./gs`, `gs.conf`, `gmserver.conf`, and `gsalias.conf` live in `$SERVER_PATH/gamed`
— adjust the `GAMED` path at the top of the script if your layout differs.

### Permissions

The service user needs write access to the game server config files. If you run the service as `www-data` (recommended when Apache is already serving a PHP admin panel on the same host):

```bash
sudo chown -R www-data:www-data /path/to/pwadmin-py
```

To allow the service to control the game server via systemctl and run the per-zone script, add a sudoers rule:

```bash
echo "www-data ALL=(ALL) NOPASSWD: /bin/systemctl start pwserver, /bin/systemctl stop pwserver, /bin/systemctl restart pwserver, /home/gs_zone.sh" \
  | sudo tee /etc/sudoers.d/pwadmin
sudo chmod 440 /etc/sudoers.d/pwadmin
```

Replace `www-data` with your service user and `/home/gs_zone.sh` with your actual script path if different.

## Deploy updates

The service runs uvicorn with `--reload`, so code and template changes are picked up automatically after a git pull — no restart needed.

```bash
# On the server (run as or via the service user)
sudo -u www-data git -C /path/to/pwadmin-py pull
```

If you update `server/pwadmin.service` itself:

```bash
sudo cp /path/to/pwadmin-py/server/pwadmin.service /etc/systemd/system/pwadmin.service
sudo systemctl daemon-reload
sudo systemctl restart pwadmin
```
