# pw_expfix_155.so — rate-bonus patch for PWI 1.5.5 (10.0.0.230)

`LD_PRELOAD` shared object that hot-patches `/home/gamed/gs` on **10.0.0.230** so that
`ptemplate.conf`'s `[GENERAL]` keys `exp_bonus`, `sp_bonus`, `money_bonus`, and
`drop_bonus` actually do something. See
[../../docs/ptemplate-general-section.md](../../docs/ptemplate-general-section.md) first
— getting these keys into `[GENERAL]` is a *separate*, also-required fix; this patch
assumes that's already done.

## What's actually broken in the stock binary

`/home/gamed/gs` is a 32-bit ELF binary, **not stripped** (full C++ symbol names
available via `nm -C /home/gamed/gs`), which made this tractable without source. Findings
from disassembling it (`objdump -d -C /home/gamed/gs`):

- **`player_template::AdjustGlobalExpSp(int&, int&)`** at `0x08105bf2` is called exactly
  once, from `gnpc_imp::DispatchExp` — the real per-kill exp/sp distribution code. Its
  entire body is:
  ```
  push %ebp
  mov  %esp,%ebp
  leave
  ret
  ```
  A no-op. `exp_bonus`/`sp_bonus` are parsed from `ptemplate.conf` somewhere internally
  (the strings exist in the binary) but nothing ever reads them back out — the hook point
  exists, it's just never wired to anything.

- **`player_template::GetGlobalMoneyBonus(float*)`** at `0x08105bf8` is *not* a stub — it
  reads a real field off the template singleton, and `gnpc_imp::DropItemFromData` calls it
  and applies the result as `money * (1.0 + bonus)`. So `money_bonus` already worked
  before this patch, just off-by-one: `money_bonus = 10` produced **11x**, not 10x. Fixed
  by NOPing out the `fld1`/`faddp` pair that adds the `1.0`.

- **`drop_bonus` has zero support in this binary** — no string, no field, nothing. Same
  situation 1.4.2 was in before `pw_expfix.c` (see
  [../pw_expfix_1.4.2/](../pw_expfix_1.4.2/)) — replicated the same technique here:
  patch the item-roll loop count in `gnpc_imp::DropItemFromData`, and wrap the
  `DropItemFromGlobal` call site in `gnpc_imp::DropItem` so `extra_drops.sev` (gold/rare
  drops) scales too.

## Patched addresses (specific to this exact `gs` binary — see Rebuilding below)

| Symbol | Address | What's patched |
|---|---|---|
| `player_template::AdjustGlobalExpSp(int&,int&)` | `0x08105bf2` | 5-byte `E9` JMP to `real_adjust()`, which multiplies `*exp` and `*sp` by `exp_bonus`/`sp_bonus` read from `ptemplate.conf` at load time |
| `fld1`/`faddp` in `DropItemFromData`'s money calc | `0x08102123` | NOP'd (4 bytes) so `money * (1+bonus)` becomes `money * bonus` |
| Item-roll loop bound, normal mode | `0x08101f5f` (imm32 inside `movl $1, -0x148(%ebp)`) | Overwritten with `drop_bonus` |
| Item-roll loop bound, event mode | `0x08101f53` (imm32 inside `movl $2, -0x148(%ebp)`) | Overwritten with `drop_bonus * 2` |
| `call DropItemFromGlobal` inside `gnpc_imp::DropItem` | `0x08102287` (targets `0x08101bca`) | Retargeted to `my_drop_global`, a trampoline that calls the real function `drop_bonus` times |

## Building

Needs a 32-bit toolchain (the target `gs` is i386, the server is otherwise x86-64):

```bash
# one-time, on 10.0.0.230
apt-get install gcc-multilib libc6-dev-i386   # i386 arch must already be enabled:
                                                # dpkg --add-architecture i386 && apt-get update

cd /home/gamed
gcc -m32 -shared -fPIC -nostartfiles -o pw_expfix_155.so pw_expfix_155.c
```

Must be built (or at least the final `.so` copied to) `/home/gamed/` on 10.0.0.230 — it
reads `/home/gamed/ptemplate.conf` at load time via a hardcoded path, matching the
`gs` process's own working directory.

## Deploying

1. Copy `pw_expfix_155.c` and the compiled `pw_expfix_155.so` to `/home/gamed/` on
   10.0.0.230.
2. `/home/start.sh`'s `gs` launch line must set the env var:
   ```sh
   cd $PW_PATH/gamed; LD_PRELOAD=./pw_expfix_155.so ./gs gs01 gs.conf gmserver.conf gsalias.conf is61 >$PW_PATH/logs/gs01.log 2>&1 &
   ```
3. `gs.conf`'s `RestartShell` (`/home/gamed/config/world/restart2`) needs the same
   `LD_PRELOAD` — see [../restart2_selfheal_fix/](../restart2_selfheal_fix/). This is
   `gs`'s own internal crash-recovery path (separate from `start.sh`), and forgetting it
   here silently drops the patch if that path is ever exercised.
4. Restart `gs` (`systemctl restart pwserver`, or manually kill + relaunch the `./gs`
   process — **check nobody's online first**, this drops all connections).

Normal in-game instance/arena spawning (players zoning into dungeons, etc.) does **not**
need any of this — those are `fork()`ed from the already-running, already-patched `gs`
process and inherit `LD_PRELOAD` automatically. Verified directly via
`cat /proc/<pid>/maps | grep pw_expfix` on both the main `gs01` process and a
dynamically-listed instance (`is61`) — both had the `.so` mapped from one `LD_PRELOAD`
on the parent invocation.

## Verifying it's loaded

```bash
cat /proc/$(pgrep -f 'gs gs01')/maps | grep pw_expfix_155
```
Should show 5 mapped segments (r--p / r-xp / r--p / r--p / rw-p). If nothing loaded, `gs`
started without the env var — check `start.sh`/`restart2`, and check `gs01.log` for
loader errors (`gcc -m32` build issues usually show up as `cannot open shared object
file` or `wrong ELF class` if a 64-bit `.so` slipped in by mistake).

## Rebuilding after a `gs` binary upgrade

**Every address above is specific to the exact compiled `gs` binary this was built
against.** If the binary is ever replaced (patch, upgrade, different build), all of them
need to be re-derived:

```bash
nm -C /home/gamed/gs | grep -i 'AdjustGlobalExpSp\|GetGlobalMoneyBonus\|DropItemFromData\|DropItemFromGlobal\|DropItem('
objdump -d -C /home/gamed/gs > /tmp/gs_disasm.txt   # this file is large (hundreds of MB)
```
Then walk each function's disassembly the same way this patch's addresses were found
(documented inline in `pw_expfix_155.c`'s comments) and update the `#define`s. A binary
that's been re-linked/re-optimized even slightly can shift every one of these addresses,
so don't assume they're stable across even a minor server update.

## Config semantics (`/home/gamed/ptemplate.conf`, inside `[GENERAL]`)

```ini
exp_bonus = 10      ; 10x EXP
sp_bonus  = 100     ; 100x SP
money_bonus = 10    ; 10x coin drops (was 11x before this patch's NOP fix)
drop_bonus = 0      ; N item/gold drop rolls per kill; 0 or missing = normal rate
```
Read once at `gs` process startup (in the `.so`'s constructor) — changing these values
requires restarting `gs`, they are not polled live.
