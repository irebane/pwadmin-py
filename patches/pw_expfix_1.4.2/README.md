# pw_expfix.so — rate-bonus patch for PWI 1.4.2 (10.0.0.240)

`LD_PRELOAD` shared object that hot-patches `/home/gamed/gs` on **10.0.0.240** so that
`ptemplate.conf`'s `[GENERAL]` keys `exp_bonus`, `sp_bonus`, `money_bonus`, and
`drop_bonus` actually do something. This patch already existed on the server and was
already wired into `/home/start.sh` before this repo tracked it — this is the first time
it's been version-controlled and documented rather than existing only as a loose `.c`
file on the box. It's the direct predecessor of
[../pw_expfix_1.5.5/](../pw_expfix_1.5.5/), built for 10.0.0.230 using the same
technique against a different `gs` binary with different addresses.

## What's broken in the stock binary

Same class of bug as 1.5.5 (see that patch's README for the general shape of the
problem): the 1.4.2 `gs` binary has an `AdjustGlobalExpSp`-equivalent stub at
`0x080b9c04` that does nothing on its own — exp/sp bonus multipliers live in a
per-class player-template struct (`PLAYER_TEMPLATE_BASE`, offsets `0x16dc`/`0x16e0` for
exp/sp bonus) that the stub never reads. Unlike 1.5.5, `drop_bonus` support is also
completely absent here — same item-roll-loop-count + `DropItemFromGlobal`-call-site
technique is used to add it.

## Patched addresses (specific to 10.0.0.240's exact `gs` binary)

| Symbol / location | Address | What's patched |
|---|---|---|
| exp/sp adjust stub | `0x080b9c04` | 5-byte `E9` JMP to `real_adjust()`, which reads `exp_bonus`/`sp_bonus` from the live player-template struct at `PLAYER_TEMPLATE_BASE` (`0x08956be0`) and multiplies `*exp`/`*sp` |
| Money `fld1`/`faddp` in `DropItemFromData`-equivalent | `0x080b715a` | NOP'd (4 bytes) so `money * (1+bonus)` becomes `money * bonus` |
| Item-roll loop bound, normal mode | `0x080b6fb4` | Overwritten with `drop_bonus` |
| Item-roll loop bound, event mode | `0x080b6fa8` | Overwritten with `drop_bonus * 2` |
| `call DropItemFromGlobal`-equivalent | `0x080b72bd` (targets `0x080b6c42`) | Retargeted to `my_drop_global`, a trampoline that calls the real function `drop_bonus` times |

Full context and byte-level detail is in the comments inside `pw_expfix.c` itself.

## Building

```bash
# on 10.0.0.240
gcc -m32 -shared -fPIC -nostartfiles -o pw_expfix.so pw_expfix.c
```

Must live in `/home/gamed/` — it reads `/home/gamed/ptemplate.conf` at load time via a
hardcoded path matching `gs`'s working directory.

## Deployment (already live on 10.0.0.240)

`/home/start.sh` sets `LD_PRELOAD=./pw_expfix.so` on **both** `gs` launch lines — this
server runs the main world (`gs01`) and all arena/instance zones as two separate `gs`
invocations (unlike 1.5.5's single invocation), and both need the env var independently:

```sh
cd $PW_PATH/gamed; LD_PRELOAD=./pw_expfix.so ./gs gs01 >$PW_PATH/logs/game1.log 2>&1 &
...
cd $PW_PATH/gamed
LD_PRELOAD=./pw_expfix.so ./gs $FIRST gs.conf gmserver.conf gsalias.conf $REST 2>&1 | \
    grep -av "OnAbortSession" >>$PW_PATH/logs/game_all.log &
```

`start.sh` on this server also supports per-zone enable/disable via
`gamed/disabled_zones.txt` — a zone listed there is skipped entirely on startup rather
than launched.

## Verifying it's loaded

```bash
cat /proc/$(pgrep -f 'gs gs01')/maps | grep pw_expfix
```

## Config semantics (`/home/gamed/ptemplate.conf`, inside `[GENERAL]`)

```ini
exp_bonus   = 10   ; 10x EXP
sp_bonus    = 10   ; 10x SP
money_bonus = 10   ; 10x coin drops from mobs
drop_bonus  = 10   ; 10x item drop rolls per mob kill (element.data + extra_drops.sev)
```

As on 1.5.5, this file must have these keys inside `[GENERAL]` specifically — see
[../../docs/ptemplate-general-section.md](../../docs/ptemplate-general-section.md). This
patch's own config reader scans the whole file for a unique key name regardless of
section, so it isn't affected by section placement itself — but the *game engine's*
`exp_bonus`/`sp_bonus`/`money_bonus` parsing (for the parts of the value this patch
doesn't fully own) is, so keep them in `[GENERAL]` regardless.

## Rebuilding after a `gs` binary upgrade

Every address above is specific to this exact compiled `gs` binary. If it's ever
replaced, all of them need to be re-derived by disassembling the new binary and locating
the equivalent stub/loop/call-site — see
[../pw_expfix_1.5.5/README.md](../pw_expfix_1.5.5/README.md)'s "Rebuilding" section for
the general method (that binary happened to be unstripped, making it much easier; if
1.4.2's `gs` is stripped, the equivalent functions will need to be found by pattern/logic
rather than by symbol name).
