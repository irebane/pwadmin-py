# pw_instance_watch.so — zone-switch probe for PWI 1.5.5 (10.0.0.230)

`LD_PRELOAD` shared object that observes every call to
`world_manager::PlaneSwitch(gplayer_imp*, A3DVECTOR const&, int, instance_key const&, unsigned int)`
— the single, non-virtual function that handles a player's zone-switch request (portal,
teleport item, etc). **Purely observational: does not alter game behavior.** Logs each
call's arguments to `/tmp/pw_switch_watch.log`, which `app/services/instance_watch.py`
tails to drive the Instance Autostart feature. See
[../../docs/zone-lifecycle-and-gm-protocol.md](../../docs/zone-lifecycle-and-gm-protocol.md)
for the full investigation behind this (including what *doesn't* go through `PlaneSwitch`
— notably, login/character-resume into an offline zone doesn't fire this hook at all).

How the hook works, why `PlaneSwitch` specifically (not the two virtual
`HandleSwitchRequest` overrides tried first), and the trampoline/stolen-bytes technique
are all documented inline in `pw_instance_watch.c`'s header comment — read that before
touching the code.

## Prebuilt `.so`

`pw_instance_watch.so` in this directory is the exact binary running in production,
committed alongside the source for the same reason as
[../pw_expfix_1.5.5/](../pw_expfix_1.5.5/): anyone running an identical build of the PWI
1.5.5 `gs` binary can use it as-is. **The same compatibility caveat applies** — the single
hardcoded hook address (`PlaneSwitch` at `0x081bef10`) is specific to this exact compiled
binary. Confirm your `gs` matches before trusting it (see
[../pw_expfix_1.5.5/README.md](../pw_expfix_1.5.5/README.md#prebuilt-so) for how to check),
and rebuild from source instead if it doesn't — a mismatched address will patch the wrong
instruction bytes at process startup.

## Building

Same 32-bit toolchain as [../pw_expfix_1.5.5/](../pw_expfix_1.5.5/):

```bash
cd /home/gamed
gcc -m32 -shared -fPIC -nostartfiles -o pw_instance_watch.so pw_instance_watch.c
```

## Deploying

Load alongside `pw_expfix_155.so` in the same `LD_PRELOAD` (space-separated, order
doesn't matter — the two hooks patch unrelated addresses):

```sh
cd $PW_PATH/gamed; LD_PRELOAD="./pw_expfix_155.so ./pw_instance_watch.so" ./gs gs01 gs.conf gmserver.conf gsalias.conf is61 >$PW_PATH/logs/gs01.log 2>&1 &
```

This patch can be loaded or dropped independently of `pw_expfix_155.so` — they hook
different, unrelated addresses and don't interact. Same restart/connection-drop caveats
apply as `pw_expfix_155.so`'s deploy steps, and the same `restart2` `LD_PRELOAD` path
(see [../restart2_selfheal_fix/](../restart2_selfheal_fix/)) needs updating too if you
want the watcher to survive `gs`'s internal crash-recovery restarts.

## Verifying it's loaded

```bash
cat /proc/$(pgrep -f 'gs gs01')/maps | grep pw_instance_watch
```

Then trigger a real zone switch (portal/teleport) and confirm a new line lands in
`/tmp/pw_switch_watch.log`:

```bash
tail -f /tmp/pw_switch_watch.log
```

## Log format

```
<unix_sec>.<nanosec> [PlaneSwitch] this=<world_manager*> player=<gplayer_imp*> pos=<A3DVECTOR*> worldtag=<uint> ikey_ptr=<instance_key*> flag=<uint> ikey_bytes=<64 hex chars>
```

`worldtag` is the value that matters — it's compared directly against
`world_manager::_world_tag` in the disassembly and identifies which zone the player is
switching into. `ikey_bytes` is the raw 32-byte `instance_key` struct dumped for forward
compatibility; its layout isn't decoded (not needed for the current use case).

## Log rotation

Self-contained inside the `.so` (see the "Log rotation" note in `pw_instance_watch.c`'s
header comment) — truncates `/tmp/pw_switch_watch.log` in-process once it exceeds 5MB,
rather than needing `www-data` (which only reads the file) to have write/truncate access
to a root-owned log.

## Rebuilding after a `gs` binary upgrade

Same caveat as [../pw_expfix_1.5.5/](../pw_expfix_1.5.5/#rebuilding-after-a-gs-binary-upgrade)
— the hardcoded `PlaneSwitch` address must be re-derived from the new binary:

```bash
nm -C /home/gamed/gs | grep PlaneSwitch
objdump -d -C /home/gamed/gs > /tmp/gs_disasm.txt
```

Find the new address and update `HOOKS[]` in `pw_instance_watch.c`. Also re-verify
`stolen_len` still lands on an instruction boundary at the new address — it's specific to
the exact bytes present there, not just the function's identity.
