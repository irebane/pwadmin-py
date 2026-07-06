# Example server config files

Real config files from a live PWI 1.5.5 deployment, included so you can see the exact
format `app/services/server_config.py` reads and writes when you use the **Server
Config** page's Save action — reverse-engineering the key names/sections from scratch
isn't required.

Checked for anything private before committing: no credentials, no external IP addresses
(everything here is `127.0.0.1`/`0.0.0.0`/internal socket config), no account or player
data. The `exp_bonus`/`sp_bonus`/`money_bonus`/`drop_bonus` values in `ptemplate.conf` are
this specific server's current live tuning (10x/100x/10x/10x) — not defaults, and not
something to copy verbatim; set your own.

| File | Real path | Daemon | What pwadmin-py touches |
|---|---|---|---|
| [ptemplate.conf](ptemplate.conf) | `$SERVER_PATH/gamed/ptemplate.conf` | `gs` (gamed) | `[GENERAL]` rate-bonus keys — see [docs/ptemplate-general-section.md](../../docs/ptemplate-general-section.md) for a section-placement bug that affects this exact file |
| [gamed_gmserver.conf](gamed_gmserver.conf) | `$SERVER_PATH/gamed/gmserver.conf` | `gs` (gamed) | Rebuilt when the `glinkd` instance count changes (`_rebuild_gmserver_conf()`) |
| [gamedbd_gamesys.conf](gamedbd_gamesys.conf) | `$SERVER_PATH/gamedbd/gamesys.conf` | `gamedbd` | `[ThreadPool]` worker count |
| [uniquenamed_gamesys.conf](uniquenamed_gamesys.conf) | `$SERVER_PATH/uniquenamed/gamesys.conf` | `uniquenamed` | `[ThreadPool]` worker count |
| [gdeliveryd_gamesys.conf](gdeliveryd_gamesys.conf) | `$SERVER_PATH/gdeliveryd/gamesys.conf` | `gdeliveryd` | `[ThreadPool]` worker count |

## Encoding gotcha

`gamedbd_gamesys.conf` is **not UTF-8** — `file` reports it as ISO-8859, and the original
stock file mixes in Latin-1/GBK-ish bytes from legacy Chinese comments elsewhere in this
config family (see the garbled `#` comment lines near the end of `ptemplate.conf` for the
same phenomenon). That's why `server_config.py` opens this one file specifically with
`encoding="latin-1"` while everything else uses `encoding="utf-8", errors="replace"` — if
you ever add a new config file to this feature, check its actual encoding first rather
than assuming UTF-8.
