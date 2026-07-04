# `ptemplate.conf` rate keys must live in `[GENERAL]`

## The bug

`ptemplate.conf` is an ini-style file with `[SECTION]` blocks (`[GENERAL]`, `[SWORDSMAN]`,
`[MAGE]`, ... `[FAIRY]`, `[MESMD_ADJUST]`, etc). The `gs` binary's own config parser
(`playertemplate.cpp`) only reads `exp_bonus`, `sp_bonus`, and `money_bonus` from inside
`[GENERAL]` — confirmed by disassembling the binary's string table, where `GENERAL`,
`debug_command_mode`, `logic_level_limit`, `allow_login_class_mask`, `exp_bonus`,
`sp_bonus`, `money_bonus` all sit contiguously as one parsed key group. A key with the
right name anywhere else in the file (even one line after `[FAIRY]`) is silently ignored
— no error, no log line, nothing. The file *looks* correct to a human skimming it.

On 10.0.0.230 this happened for real: `exp_bonus`/`sp_bonus`/`money_bonus`/`drop_bonus`
had been appended to the end of the file, after `[FAIRY]`, instead of inside `[GENERAL]`
near the top. The admin panel dutifully displayed "10x" because it was reading the same
misplaced lines back — it wasn't lying, it just wasn't checking placement either.

## Why pwadmin-py did this to itself

`app/services/server_config.py`'s `update_conf_key()` / `parse_conf_key()` treat the
whole file as one flat list of `key = value` lines with no notion of sections. When a
key didn't already exist anywhere in the file, `update_conf_key()` fell back to
appending it to **end-of-file** — which, on a file whose last section happens to be
`[FAIRY]`, means the key lands inside `[FAIRY]`, not `[GENERAL]`. The read path
(`parse_conf_key()`) has the mirror-image bug: it returns the first match anywhere in
the file, so it happily read back and displayed the misplaced value as if it were live.

## The fix

`parse_conf_key_in_section()` / `update_conf_key_in_section()` in `server_config.py`
locate the named section's body (from its `[HEADER]` line to the next `[HEADER]` line or
EOF) and only read/write within those bounds. `update_conf_key_in_section()` creates the
section at the top of the file if it's missing entirely, and never falls back to a blind
end-of-file append. `read_game_config()` / `save_game_config()` now call these for
`ptemplate.conf`'s `debug_command_mode`, `allow_login_class_mask`, `exp_bonus`,
`sp_bonus`, `drop_bonus`, and `money_bonus` — all of which the game engine expects inside
`[GENERAL]`.

The other `update_conf_key()`/`parse_conf_key()` call sites (`gamesys.conf` keys like
`pvp`, `battlefield`, `max_name_len`) were left on the old flat-file functions — those
keys are unique across their files in practice and aren't gated by section placement in
the binary, so the section-blind behavior there isn't a bug, just wouldn't be an
improvement.

## This is a necessary but not sufficient fix

Getting `exp_bonus`/`sp_bonus` into the right section makes the *config file* correct.
It does **not** mean the game server actually applies them — on 10.0.0.230 the function
that's supposed to multiply exp/sp per kill turned out to be a compiled no-op in the
shipped binary regardless of what the config says. See
[../patches/README.md](../patches/README.md) for that half of the fix. Both bugs produce
the identical symptom ("I set 10x, I'm getting 1x"), so don't assume fixing one means the
other doesn't also need checking.
