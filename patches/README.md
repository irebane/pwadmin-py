# Server-side patches

This directory holds custom fixes that live on the game servers themselves (compiled
binary patches, shell scripts) rather than in pwadmin-py's own code. They're kept here
so they're version-controlled and documented instead of existing only as loose files on
each server.

Both live PWI servers ship `gs` binaries with dead/incomplete rate-bonus code — the
`ptemplate.conf` keys `exp_bonus`/`sp_bonus`/`money_bonus`/`drop_bonus` don't do what the
stock binary's own documentation implies unless these patches are applied. See
[../docs/ptemplate-general-section.md](../docs/ptemplate-general-section.md) for the
config-side half of this story (a section-placement bug that looks like the same
symptom but is a completely different bug).

| Directory | Server | Problem it solves |
|---|---|---|
| [pw_expfix_1.4.2/](pw_expfix_1.4.2/) | 10.0.0.240 (PWI 1.4.2) | exp/sp/drop bonus stubs are no-ops in the stock `gs` binary |
| [pw_expfix_1.5.5/](pw_expfix_1.5.5/) | 10.0.0.230 (PWI 1.5.5) | same class of bug, different binary/addresses, plus money_bonus off-by-one and missing drop_bonus support entirely |
| [pw_instance_watch_1.5.5/](pw_instance_watch_1.5.5/) | 10.0.0.230 (PWI 1.5.5) | observational probe for zone-switch calls, backs the Instance Autostart feature |
| [restart2_selfheal_fix/](restart2_selfheal_fix/) | 10.0.0.230 (PWI 1.5.5) | `gs`'s internal crash-recovery script pointed at a nonexistent path and didn't load the LD_PRELOAD patch |

## Why these exist

Both `gs` binaries are 32-bit ELF binaries shipped without source, so nothing here can
be "fixed properly" in the sense of patching original source and recompiling — we don't
have the source. Instead, each fix is an `LD_PRELOAD` shared object that hot-patches the
already-loaded binary's machine code at process startup (via a `__attribute__((constructor))`
that calls `mprotect()` + overwrites specific instruction bytes at addresses found by
disassembling the binary with `objdump -d -C` against its own symbol table — both
binaries are `not stripped`, so full C++ symbol names are available via `nm -C`).

This is inherently binary-specific: if a server's `gs` binary is ever replaced/upgraded,
every hardcoded address in these patches needs to be re-derived from the new binary and
the `.so` recompiled. They will not work as-is against a different build.

## Prebuilt `.so` files

`pw_expfix_1.5.5/` and `pw_instance_watch_1.5.5/` each include the exact compiled `.so`
running in production, alongside their source. These are committed as a convenience for
anyone running an identical `gs` build (common across copies of the same server pack) —
**not** a claim of universal compatibility. Each directory's README explains how to
verify your binary matches before trusting the prebuilt file, and how to rebuild from
source if it doesn't. `pw_expfix_1.4.2/` has no prebuilt `.so` since 10.0.0.240 is out of
scope for this repo going forward.
