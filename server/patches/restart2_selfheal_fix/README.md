# restart2 — gs internal crash-recovery script fix (10.0.0.230)

Fixes `/home/gamed/config/world/restart2` on **10.0.0.230**, the script `gs` itself
invokes via its own `RestartShell` config setting (`gs.conf`, `[Template]` section:
`RestartShell = restart2`) — this is `gs`'s *internal* self-healing mechanism, separate
from `/home/start.sh` and separate from normal in-game instance/arena spawning.

## The bug

The file shipped in `/home/gamed/config/world/restart2` was an untouched leftover from
the original 2013 build (`Modify` timestamp: `2013-09-18`):

```sh
#!/bin/sh

/usr/bin/killall gs
/bin/sleep 8
cd /home/zhangyu/game
./gs gs01>game1.log&
./gs arena01  gs.conf gmserver.conf gsalias.conf arena02 arena03 arena04 is01 is02 is05 is06 is07 is08 is09 is10 is11 is12 is13 is14 is15 is16 is17 is18 is19 is20 is21 is22 is23 is24 is25 is26 bg01 bg02 bg03 bg04 bg05 bg06 > game_all.log
```

Three separate problems:

1. `cd /home/zhangyu/game` — that directory doesn't exist on this server at all (leftover
   from the original developer's build environment). If this script is ever actually
   invoked, the `cd` fails and `gs` never relaunches — the "self-healing" path leaves the
   server **fully down** instead of recovering it.
2. Doesn't include `is61` in the relaunch args, unlike the real invocation in
   `start.sh` — an incomplete zone list even if the path were fixed.
3. No `LD_PRELOAD` — even if this had otherwise worked, it would silently relaunch `gs`
   *without* [../pw_expfix_1.5.5/](../pw_expfix_1.5.5/) loaded, reverting exp/sp/drop
   rates to stock (broken) behavior with no visible error.

This was discovered while auditing "will map starting/stopping break the rate patch,"
not by observing it actually fire — there's no evidence in `catalina.out` or `gs01.log`
that `RestartShell` has ever actually been triggered on this server. It's a dormant bug,
found and fixed pre-emptively.

## The fix

`restart2` (this directory) matches `start.sh`'s real invocation:

```sh
#!/bin/sh

killall gs
sleep 8
cd /home/gamed
LD_PRELOAD=./pw_expfix_155.so ./gs gs01 gs.conf gmserver.conf gsalias.conf is61 >/home/logs/gs01.log 2>&1 &
```

## Deploying

```bash
cp /home/gamed/config/world/restart2 /home/gamed/config/world/restart2.bak-$(date +%Y%m%d-%H%M%S)
scp restart2 root@10.0.0.230:/home/gamed/config/world/restart2
ssh root@10.0.0.230 "chmod 755 /home/gamed/config/world/restart2"
```

Already deployed as of 2026-07-03 (backup left at
`/home/gamed/config/world/restart2.bak-20260703-224742`).

## If `start.sh`'s launch line ever changes

This script needs to be kept in sync manually — it's a second, independent copy of the
same `./gs gs01 gs.conf gmserver.conf gsalias.conf is61` invocation. If the zone list,
config file names, or `LD_PRELOAD` target (e.g. after
[rebuilding pw_expfix_155.so](../pw_expfix_1.5.5/README.md#rebuilding-after-a-gs-binary-upgrade))
ever changes in `start.sh`, update this file to match or the self-heal path will silently
drift out of sync again.

## Known drift (as of 2026-07-06)

Exactly the scenario warned about above has already happened once:
[`pw_instance_watch_1.5.5`](../pw_instance_watch_1.5.5/) was added after this fix
(2026-07-03) and `start.sh` was updated to
`LD_PRELOAD="./pw_expfix_155.so ./pw_instance_watch.so"`, but this `restart2` was never
updated to match — it still only sets `LD_PRELOAD=./pw_expfix_155.so`. Not urgent (no
evidence `RestartShell` has ever actually fired on this server, same as the original bug
this file fixed), but if it ever does, the zone-switch watcher would silently stop
working after a self-heal while the rate patch keeps working. Fix is a one-line change to
add `./pw_instance_watch.so` to the `LD_PRELOAD` value above, then redeploy per
[Deploying](#deploying).
