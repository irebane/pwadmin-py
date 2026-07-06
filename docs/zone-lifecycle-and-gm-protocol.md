# How zone start/stop actually works, and what the GM protocol can and can't do

## Background

On 10.0.0.230, several `World_*`-type zones (`is01`, `is12`, `is19`, `is33`, ...) appeared to
start fine via `gs_zone.sh` (process launches, binds its port, registers with the provider
mesh) but couldn't actually be entered in-game ("Can't Enter Instance"). Investigation ruled
out process health, network registration, OOM, cron, systemd, and MySQL's event scheduler —
all clean. The real cause turned out to be unrelated to zone health: pwadmin-py's own
`GS_ZONES` name table in `.env` had wrong names for a chunk of the `is01`-`is33` range (e.g.
`is33` was labeled "Secret Passage" when that's actually `is02`; `is12` was labeled
"Wraithgate" when that's actually `is14`). Players were hunting for the wrong in-game
entrance because pwadmin-py told them the wrong name. Fixed by cross-referencing three
independent vendor-native sources extracted from the 1.5.5v156 reference tree (two English
Tomcat-compiled `serverctrl.jsp` name arrays + one Russian `instance.jsp` array) — see git
history for `.env` / `.env.example`.

Two side-investigations from that debugging session are worth keeping on record, since they
directly bear on any future "smarter" zone management in pwadmin-py.

## Finding 1: `gs01` + `is61` share a process, most zones don't — and it doesn't matter

`/home/start.sh` launches the main world and `is61` as **one command with two zone names**:

```sh
./gs gs01 gs.conf gmserver.conf gsalias.conf is61 &
```

The `gs` binary forks an internal child per extra zone name (that's why `is61` shows up as a
second PID but writes to `gs01`'s log file). There's even a commented-out line in `start.sh`
showing this was originally meant to scale further — all the `World_*` zones bundled into one
big multi-name invocation, rather than started individually.

This looked like a promising lead (bundle `is33` into the same invocation as `gs01`, see if
that's what makes `is61` special) — **it wasn't**. Restarting `gs01` with `is61` and `is33`
both as arguments still left `is33` unenterable. `is61` works because it's a genuine
`[Instance_is61]` zone under the hood (has `instance_capacity`/`pool_threshold_*` pooling
config); the stray `[World_is61]` header above it in `gs.conf` is vestigial. Process bundling
is a red herring — don't waste time on it again.

## Finding 2: the GM control protocol (what `iweb`/`pwadmin` Java panels actually send)

Decompiled `protocol/DeliveryDB.class` and `protocol/DeliveryClientManager.class` from the
1.5.5v156 reference tree's `iweb` webapp (`WEB-INF/classes/protocol/`, CFR 0.152) to see how
the official admin panels start/stop zones over the network, since that seemed like a cleaner
path than shelling out to `gs_zone.sh`.

**Two separate ports on `gdeliveryd`:**
- `29300` — where `gs`/`glinkd` processes connect *as providers* (register a zone, get
  `announceproviderid`, etc). This is the mesh we already talk to indirectly by launching `gs`
  processes.
- `29100` — a **separate GM/admin control port**, confirmed in `iweb.conf`
  (`[DeliveryClient] port = 29100`). This is what the Java admin panels connect to. It's open
  and listening on 10.0.0.230 right now. In principle pwadmin-py could speak to it directly
  without needing Tomcat/Java in the loop at all.

**Wire format:** proprietary binary RPC, not Hessian/REST — `Protocol.Create("GMControlGame")`
followed by custom `OctetsStream` marshaling, framed over a persistent TCP session that opens
with an `AnnounceLinkType` handshake.

**What the protocol can actually do — this is the important part:**
- `GMControlGame(worldtag, command)` — sends a text command (GBK-encoded) to an
  **already-connected** worldtag. Used for things like `active_npc_generator <id>` or
  broadcast/double-drop toggles (see `iweb`'s `manage/AA/cmd.jsp`). Requires the zone to
  already be up so `gdeliveryd` knows how to route to it.
- `GMRestartServer(gmroleid, restart_time)` — schedules a restart of **all** worlds after N
  seconds (`worldtag=-1`). This is "stop everything," not "stop one zone."
- Various `GMGetGameAttri`/`GMSetGameAttri` calls — server-wide toggles (double exp, no-trade,
  etc), not zone lifecycle.

**There is no RPC to start a zone, anywhere in this codebase, official tooling included.**
Every "start" — in `iweb`'s `instance.jsp`, in the legacy PHP panel, in pwadmin-py's
`gs_zone.sh` — is the same thing: fork `./gs <zone> gs.conf gmserver.conf gsalias.conf` as an
OS process and wait for it to bind its port. There is likewise no "stop this one zone" RPC —
`kill -15 <pid>` (what `gs_zone.sh` already does) is the only per-zone stop mechanism that
exists anywhere, including in the official admin panel's own `stopmap` action
(`Runtime.getRuntime().exec("kill " + pid)` — same approach, just from Java instead of a shell
script).

## Implication for building "smarter" zone management

- **Auto-stop idle zones**: fully buildable without touching the GM protocol at all. Each zone
  listens on a known TCP port (`is01` → 10911, `is12` → 10922, etc, see `gs.conf`
  `MsgReceiverTCP_*` sections). Poll `ss -tn` for established connections to each running
  zone's port, track a last-seen-active timestamp per zone, call the existing
  `gs_zone.sh stop <zone>` once idle past a threshold. No protocol reverse-engineering needed.
- **Auto-start on demand** (triggered by a player actually trying to enter an offline zone):
  much harder. Nothing in this stack logs or signals "a player just requested entry to zone X
  and it's not running" — `gdeliveryd`'s own log output is nearly silent (observed: one line,
  ever, across a full session: `zoneid=1 aid=1`). The only way to detect that event would be
  passively sniffing raw client↔`gdeliveryd`/`gs01` traffic and reverse-engineering the
  specific "enter instance" request opcode from scratch. That's a real protocol-RE project, not
  a config change — scope it separately if it's still wanted after idle-shutdown ships.

## Community practice: does anyone else do dynamic zone management?

Researched this before building anything, to avoid reinventing (or missing) a known pattern.
Short answer: **no** — running maps on-demand with idle shutdown is not an established practice
anywhere in the PW private-server ecosystem, as far as public sources show.

- Every tutorial/setup guide found (classic blogspot-era guides, the vendor reference tree
  itself) treats "start a map" as a one-time manual action per zone at boot, left running
  indefinitely.
- `oss-perfectworld/perfectworld` — a modern (2023-era) Docker/microservices rewrite of the
  1.5.5 stack, one container per subsystem — still runs `gamed` (the zone server) as a single
  `restart: always` container, started once, never scaled or cycled. No idle detection, no
  per-zone containers, nothing dynamic, even in an architecture that would make it easy to add.
- Couldn't find any forum/wiki discussion (elitepvpers, ecatomb.net mirrors, fandom wikis — several
  of these are dead/paywalled as of this writing) of idle-timeout or on-demand instance loading
  as a concept at all for this codebase family.

The closest thing to "resource management" that does exist anywhere, including in our own
`gs_zone.sh`, is being *selective* about which maps you choose to run in the first place, sized
to available RAM (`MIN_FREE_MB` + staggered `startmaps`) — not starting/stopping based on live
traffic. So: idle-shutdown-after-1h would be genuinely new territory for this ecosystem, not
catching up to a known pattern. Worth building carefully and incrementally rather than assuming
prior art to lean on.

## Live packet-capture findings toward "auto-start on demand" (2026-07-05)

Attempted to find the "player requested entry to offline zone X" signal by capturing real
traffic during controlled trials: known-good entries into `is02` (running) paired with failed
entries into `is06` and `is09` (both stopped), using `tcpdump` on the relevant ports, with
precise timestamps marked on both ends of each attempt.

**The client never talks to a zone's own port.** `ss -tnp` during an active session showed the
real player connection lands on `10.0.0.230:29000`, owned by **`glinkd`**, not on `gs01`'s
`MsgReceiverTCP` port (10901) as the config might suggest. `glinkd` is the actual client-facing
gateway; it relays internally to whichever zone the player is in. Any future traffic-based
detection has to watch this channel (and the twin `glinkd` instance on 29001), not the
per-zone `MsgReceiverTCP_*` ports from `gs.conf`.

**That client↔`glinkd` channel is genuinely encrypted** — payload is high-entropy with no
recognizable structure, not a simple XOR/obfuscation. Reading zone-tag values directly out of
client traffic would require reverse-engineering the session cipher itself (a much bigger
project than a protocol dissection). Ruled out as a near-term path.

**The internal `gs01`↔`glinkd` channel (port 29301) is not encrypted** — structured binary,
matches the `OctetsStream`-style framing seen in the decompiled Java admin protocol. This is
the promising channel. However, isolating the actual one-shot "enter zone X" request inside it
is harder than expected because of two independent, unrelated noise sources that both produce
false-positive matches when naively grepping for a zone's raw tag value:

1. A **~2 second periodic heartbeat** between every `gs` process and `glinkd`/`gdeliveryd`
   (constant, unrelated to player actions) containing what looks like an incrementing
   counter/sequence field. Over any capture window longer than a few seconds, that counter
   will pass through small integer values that coincidentally match a zone's tag number,
   producing lots of false hits.
2. **Tomcat is actually running** (see below) and independently polls `gdeliveryd`'s admin
   port (29100) roughly every 2 minutes per `DeliveryDB`'s static `Timer.schedule(...,
   30000L, 120000L)` — producing occasional large (400-2000+ byte) bursts on a completely
   unrelated port/purpose that can look like a "real event" if a capture window happens to
   overlap one.

Net result: raw byte-signature grepping across a capture window is not reliable enough on its
own. The real request is almost certainly a genuinely rare, low-frequency event buried in that
29301 stream, but finding it needs one of:
- much tighter time correlation (sub-second precision between "click" and packet), across
  several more trials targeting *different* zones, to see which byte position's value tracks
  the requested zone consistently rather than coincidentally, or
- a known opcode/struct layout for the internal enter-request message (would need to find or
  derive the C++ side's protocol definitions, not just the Java admin client's), or
- giving up on passive sniffing and instrumenting the binary directly (e.g. `LD_PRELOAD`
  shim intercepting `send()`/`recv()` on `gs01`, since one is already used for
  `pw_expfix_155.so` — same technique, different purpose).

**Side discovery: Tomcat (hosting `iweb` + `pwadmin` Java webapps) actually runs on this box.**
Earlier in this investigation we'd confirmed Tomcat was *not* running and concluded it couldn't
be the source of a prior mystery (multiple manually-started zones dying together with zero OS
trace). That conclusion needs an asterisk: Tomcat auto-starts via `/etc/rc.local`
(`/sbin/server pwAdmin start` — a legacy init mechanism, not a systemd unit, which is why
`systemctl list-units` never showed it) on every boot, and has been silently running and
talking to `gdeliveryd`'s admin port ever since our last reboot. It's plausible it was also
running during that earlier incident and never ruled out properly. Worth remembering this
exists and checking for it directly (`ps aux | grep Bootstrap`, not just `systemctl`) in any
future investigation of unexplained zone behavior.

## BREAKTHROUGH (2026-07-05): found and validated the real "enter zone X" signal

After the packet-capture approach hit a wall (client↔`glinkd` traffic is genuinely encrypted;
internal `gs01`↔`glinkd` traffic is unencrypted but drowned in unrelated periodic noise), we
switched to hooking `gs01`'s own binary directly. This worked, and is now fully validated with
live data. This section is the complete state needed to pick this up from scratch.

### The binary is a goldmine: full unstripped C++ symbols

`/home/gamed/gs` is `ELF 32-bit LSB executable, Intel i386 ... with debug_info, not stripped`.
`nm -C /home/gamed/gs` and `objdump -d -C /home/gamed/gs` give full demangled C++ symbol names
and disassembly. This is the same property the existing `pw_expfix_155.c` patch already
exploits (hardcoded absolute addresses for the exp/sp/drop-bonus fixes). Non-PIE binary, loads
at a fixed address every run (confirmed: `pw_expfix_155.c` has worked in production against
fixed addresses for a while), so hardcoded addresses are safe to rely on across restarts of the
*same compiled binary* (would need re-deriving if `/home/gamed/gs` itself is ever replaced by a
different build).

### The real hook point: `world_manager::PlaneSwitch`

Two earlier guesses were wrong and worth remembering as ruled out:
- `instance_world_manager::HandleSwitchRequest(int,int,int,int,instance_key const&)` @
  `0x08262ca2` — installed correctly (verified via live `/proc/PID/mem` read showing our `E9`
  JMP byte), never fired.
- `global_world_manager::HandleSwitchRequest(...)` @ `0x08284556` — same signature, same
  result: installed correctly, never fired.

Both are **virtual per-zone-category overrides** (confirmed: there's a `vtable for
world_manager` base class plus separate vtables for `home_`, `global_`, `mobile_`, `faction_`,
`instance_`, `parallel_`, `mnfaction_`, `trickbattle_`, `battleground_`, `countrybattle_`,
`countryterritory_world_manager` — at least 11 subclasses). Hooking them one at a time would
have meant 11 separate hooks and 11 separate risky `gs01` restarts to find the right one(s).

The actual answer is the **single common, non-virtual, base-class caller above all of them**:

```
world_manager::PlaneSwitch(gplayer_imp*, A3DVECTOR const&, int, instance_key const&, unsigned int)
@ 0x081bef10
```

Confirmed by disassembly: its 3rd argument (a plain `int`) gets compared directly against the
global `world_manager::_world_tag` (`0x093ece04`), and later passed to
`gplayer_imp::CheckInstanceTimer(int)` and used to look up the target server via
`MsgIOManager::GetGlobalServer(A3DVECTOR const&, int)`. This is the actual dispatch point for
*any* zone-switch request — walking through a portal, using a teleport item — regardless of
which `*_world_manager` subclass ultimately owns the target zone. **Confirmed live**: fires
identically for both a portal-triggered switch and a teleport-item-triggered switch.

Prologue (verified via `objdump -d -C --start-address=0x081bef10`):
```
081bef10: 55                push %ebp
081bef11: 89 e5             mov  %esp,%ebp
081bef13: 57                push %edi
081bef14: 56                push %esi
081bef15: 81 ec 90 00 00 00 sub  $0x90,%esp
```
We only steal the first 5 bytes (`55 89 e5 57 56`) — lands exactly before `sub $0x90,%esp`, no
instruction split.

Stack layout at entry (args pushed right-to-left per cdecl, `this` implicit first arg per
Itanium C++ ABI — GCC on Linux does NOT use thiscall/register passing):
```
[esp+0x00] return address
[esp+0x04] this               (world_manager*)
[esp+0x08] gplayer_imp*        (the player)
[esp+0x0c] A3DVECTOR const*    (target position)
[esp+0x10] int                 (world tag being requested — THE value we care about)
[esp+0x14] instance_key const* (pointer; struct layout still not decoded, but we don't need it)
[esp+0x18] unsigned int        (a flag / cost, e.g. teleport fee — observed 0 in all trials)
```

### The hook mechanism (generalized, in `server/patches/pw_instance_watch_1.5.5/pw_instance_watch.c`)

Key lesson learned the hard way: an early version used inline `__asm__` with `call
log_switch_request` by symbol name inside a `naked` function. GCC/GAS silently prepended PIC
GOT-thunk setup code (`call __x86.get_pc_thunk.ax; add $N,%eax`) that was never written and
shifted every hand-counted byte offset. **Never trust compiler-emitted bytes when the whole
point is knowing exact offsets** — the fix was building the entire trampoline as a manual
`static const uint8_t[]` byte array, verified independently via `objdump -s -j .rodata` against
the compiled `.so` before ever touching `gs01`.

Second lesson: don't hardcode a target function's prologue bytes as a fixed template assuming
all hook targets share one prologue shape (the two `HandleSwitchRequest` variants happened to
share a shape; `PlaneSwitch` has a different one — 5 bytes stolen, not 10, different registers
pushed). The current design instead:
1. Takes only `{tag, hook_addr, stolen_len}` per hook (`stolen_len` manually verified via
   `objdump` to land on a real instruction boundary, minimum 5).
2. At install time, **reads the actual live bytes** at `hook_addr` for `stolen_len` bytes and
   copies them verbatim into the trampoline's replay section — no need to hand-transcribe them
   into source at all, eliminating that whole class of transcription-error risk.
3. Builds a small mmap'd RWX trampoline per hook: set a tag string (for multi-hook
   disambiguation) → push the 6 stack words (`this` + 5 args) as call args → `call
   log_switch_request` (address patched in via `mmap`-time relocation, computed from the
   *runtime* resolved address of the C function — no compiler-symbol ambiguity) → clean up →
   replay the stolen bytes → `jmp` back to `hook_addr + stolen_len`.
4. Only then patches `hook_addr`'s first 5 bytes with a `JMP` into the trampoline.

**Validated twice in full isolation before ever touching `gs01`**: a standalone self-test
program (`hook_selftest.c` / `hook_selftest2.c`, built fresh each time in `/tmp` on the scratch
directory, not committed — cheap to recreate if needed) defines a dummy target function as raw
bytes with the same prologue shape, applies the exact same hook-install code, calls it, and
checks (a) the hook receives exactly the arguments passed, (b) the original function body still
runs afterward and returns its own sentinel unmodified, (c) nothing crashes. Passed both times
(once for the 10-byte-prologue shape, once for the 5-byte one) before the corresponding live
deploy.

### Confirmed live results (2026-07-05, this session)

Deployed by editing `/home/start.sh`'s `gs01` launch line to add the new `.so` to
`LD_PRELOAD` (original backed up to `/home/start.sh.bak_before_instance_watch`), then
`systemctl restart pwserver.service`. Compiled `.so` lives at `/home/gamed/pw_instance_watch.so`
on the live server (also on record in git at `server/patches/pw_instance_watch_1.5.5/pw_instance_watch.c`
— note: the compiled `.so` was built directly on 10.0.0.230 via `gcc -m32 -shared -fPIC
-nostartfiles`, not committed as a binary artifact). Logs to `/tmp/pw_switch_watch.log` on the
live server (not synced anywhere, purely observational for now).

Verified patch application by reading live process memory directly
(`/proc/<gs01 pid>/mem`, seek to hook address, read 5 bytes, confirm `E9` + a plausible rel32) —
worth doing this again after any future redeploy, don't just trust "it compiled."

Real log entries collected:
```
worldtag=102  -- portal entry into is02 ("Secret Passage"), zone WAS running -> succeeded (x2)
worldtag=106  -- portal entry into is06 ("Den of Rabid Wolves"), zone NOT running -> 4x "Can't
                 Enter Instance" (user retried), 4 matching log lines
worldtag=169  -- teleport-item entry into is69 ("LightSail Cave"), zone NOT running -> failed
```
Every entry: clean, one line per real attempt, zero false positives, zero heartbeat noise —
categorically better signal quality than anything the packet-capture approach produced. `gs01`
remained healthy (no crash, verified via process list + port-listen check) through every restart
and every test in this session.

Note on `ikey_bytes`: is02 (World_-type) calls show a different byte pattern than is06/is69
(both happen to be Instance_-type in `gs.conf`) at a few offsets — likely instance-pool-related
fields — but we don't need to decode `instance_key`'s layout at all, since arg3 already gives
the plain integer world tag directly. Not investigated further; not currently needed.

### IMPLEMENTED (2026-07-05): full autostart/auto-stop feature in pwadmin-py

All 5 items from the previous "What's NOT done yet" list are now built. Summary of the design
and where everything lives:

**`worldtag -> zone_id` map** — confirmed the guess above was wrong to rely on: tag is *not*
uniformly `100 + zone number` across the full range (e.g. `bg01..bg06` are tags 230-235,
`arena01..04` are 201-204, `ms01` is 211). Read directly from live `gs.conf` instead:
`app/services/instance_watch.py::_build_tag_zone_map()` parses every `[World_x]`/`[Instance_x]`
section for its first `tag = N` line, keyed against `settings.gs_zones_dict` so unmanaged
sections (e.g. a stray duplicate `[World_gs02__]`, also tag 1) are ignored. Verified against the
live `gs.conf` on 10.0.0.230: all 78 zones in `.env`'s `GS_ZONES` resolve to a tag, and the three
real log lines captured earlier in this doc decode correctly — `102→is02` (Secret Passage),
`106→is06` (Den of Rabid Wolves), `169→is69` (LightSail Cave, the exact teleport-item test from
this session). `gs01` (tag 1) is hardcoded-protected and never touched by the watcher — it's not
managed by `gs_zone.sh` at all, only by `start.sh`/`systemctl`.

**Watcher** — `app/services/instance_watch.py`, two asyncio background tasks started/stopped
from inside the pwadmin-py process itself (no new service/systemd unit):
- `_tail_hook_log()` polls `/tmp/pw_switch_watch.log` every 1.5s by byte offset (like `tail -f`),
  parses `worldtag=(\d+)`, resolves to `zone_id`, updates `last_activity[zone_id]`, and if the
  zone isn't currently running (`server_status.get_running_zone_ids()`, extracted as a shared
  helper — was previously private to `get_maps_status()`), calls `sudo /home/gs_zone.sh start
  <zone>` — the exact same command `app/routers/server.py`'s existing single-zone start button
  already uses. A 30s per-zone cooldown (`START_COOLDOWN_SECONDS`) prevents a player's repeated
  "Can't Enter" retries (observed 4x in the same few seconds earlier in this doc) from firing 4
  redundant starts.
- `_idle_check_loop()` runs every 5 minutes; for each currently-running, non-protected,
  non-`"world"`-type zone (same protection rule already used by "Stop Maps (Keep World)" in
  `maps_control()`), if `now - last_activity[zone_id] >= idle_minutes * 60`, calls `sudo
  /home/gs_zone.sh stop <zone>`. Zones with no recorded activity yet (e.g. already running when
  the watcher started) get a baseline seeded on first check rather than being stopped
  immediately on zero data.
- **Known limitation, by design**: `PlaneSwitch` only fires on zone *switch requests*
  (entering/leaving via portal or teleport item), not on ongoing presence. "Idle" therefore means
  "no one has switched into this zone recently" — a zone with players who never leave could
  still look idle and get stopped. There's no cheaper live per-zone player-count signal
  available without decoding the GM control protocol's player-list opcodes (not attempted).
  Documented in the UI tooltip text directly so this isn't a surprise in practice.

**Log rotation** — two independent logs, two different mechanisms since they're owned by two
different processes/users:
- `/tmp/pw_switch_watch.log` (written by the LD_PRELOAD hook running as whatever user runs
  `gs01`, i.e. root) rotates *itself*: `log_switch_request()` in
  `server/patches/pw_instance_watch_1.5.5/pw_instance_watch.c` now `stat()`s the file before each write
  and reopens with `"w"` (truncate) instead of `"a"` once it exceeds 5 MB. This avoids ever
  needing to grant the pwadmin-py process (running as `www-data`) write/sudo access to a
  root-owned file just to rotate it — it only ever needs read access, which the file's default
  644 permissions already provide.
- The pwadmin-py-side "Instance Activity" log (what the UI card shows) is capped at 300 entries
  in `instance_watch.py`'s `_log()`, self-bounding by design — same pattern as the existing
  `Activity Log` card's 200-entry cap in `app/routers/server.py`.

**Persistence** — `enabled` and `idle_minutes` persist across pwadmin-py restarts in
`data/autostart_state.json` (gitignored, created at runtime — same treatment as the pre-existing
untracked `data/activity_log.json`). Read at process startup in `app/main.py`'s `lifespan()` via
`instance_watch.init_on_startup()`, which starts the background tasks immediately if the feature
was left enabled. `instance_watch.shutdown()` cancels them cleanly on process exit.

**UI** — `templates/server/index.html`, two new cards in the right column after Map Management:
"Instance Autostart" (enable checkbox + idle-timeout minutes field, both calling `POST
/api/server/autostart`) and "Instance Activity" (paginated log, same visual pattern as the
existing Activity Log card, color-coded green/amber/red for start/stop/error, polled every 5s
alongside the existing status/maps refresh interval). New endpoints: `GET`/`POST
/api/server/autostart`.

**Deployment status as of 2026-07-05**: all code above is written and committed to the
pwadmin-py repo working tree. **Not yet deployed to the live server**:
1. The updated `pw_instance_watch.c` (rotation logic) needs recompiling
   (`gcc -m32 -shared -fPIC -nostartfiles -o pw_instance_watch.so pw_instance_watch.c`) and
   `gs01` needs restarting (`sudo systemctl restart pwserver`) to pick up the new `.so` — this
   briefly disconnects all players, same as any other `start.sh`/hook change this session.
2. The pwadmin-py app itself needs the new code deployed (`git pull` + restart, per
   `DEPLOY.md` — note `pwadmin.service` runs uvicorn with `--reload` so a `git pull` alone may
   be enough, but a restart is the more reliable/simpler option to reset in-memory watcher
   state cleanly).
3. The feature is **disabled by default** (opt-in checkbox) — nothing changes on the live
   server's behavior until the checkbox is explicitly turned on in the UI after deployment.

### CORRECTION (2026-07-05, same day): login/character-resume does NOT go through PlaneSwitch

Real-world test on live traffic: enabled the watcher, then watched `/tmp/pw_switch_watch.log`
with `tail -f` while a real account (`agilato`, userid 1040) attempted to log in 5 times over
45 seconds while their character's saved zone (`is31`) was offline. **Zero new lines appeared
in the hook log during any of those attempts.** `authd.log` confirmed the login attempts
happened (`UserLogin:userid=1040` x5) and all failed ("Couldn't login to server" client-side).

So: `PlaneSwitch` only fires for *voluntary* in-game zone switches (portal, teleport item)
while already connected — not for placing a character into their last saved position during
login/character-resume. That's a different, still-unidentified code path in the `gs01` binary.
This means the original Instance Autostart feature above does **not** cover "character's
saved zone is offline at login" at all — that failure mode was silently unfixed by the whole
feature as first built.

**Fix, without touching the binary at all**: rather than reverse-engineer the actual
login/resume placement function (a second full RE effort), solved it one layer up, using
tools pwadmin-py already had:
- `authd.log` is plaintext and already logs `UserLogin:userid=N` on every login attempt — no
  hooking needed, just tail the file (same byte-offset polling technique as the hook log).
- `app.services.game_client.GameClient.get_user_roles(user_id)` (already used by the account
  pages) queries gamedbd directly over its own binary protocol (port 29400, opcode `0xD49`
  chained into `0x1F43` per character) and returns each character's saved `world_tag` — this
  is exactly how Agilata's stuck zone was found in the first place (roleid 1024, `world_tag`
  131 → `is31`), by running the query manually. Read-only, no risk to character data.
- So: on every `UserLogin:userid=N` line, query that account's characters' `world_tag`s and
  make sure each resolved zone is running, using the exact same `_maybe_autostart()` /
  `gs_zone.sh start` path the hook-based trigger already used. A one-shot sweep over every
  account in the `users` table also runs once when the watcher starts, so a zone that died
  while the watcher was off (or before anyone tries to log in again) comes back proactively,
  not just reactively on the next failed attempt.

**Real-world negative-case data point** (why the proactive sweep matters, not just the
reactive per-login check): `is31` was manually stopped once already this session (`POST
/api/server/maps` from the admin's own browser at 02:35:47, right as Agilata's client was
still inside it) — a completely different failure path than a crash or restart, and one no
in-game signal will ever announce. The reactive login check still recovers from this exactly
as well as from a restart-caused outage, since it only cares about "is the saved zone running
right now", not why it went down.

**Still not handled**: if a zone genuinely cannot be started (e.g. permanently removed from
`gs.conf`, or `gs_zone.sh`'s `MIN_FREE_MB` memory guard blocks it), the affected character
stays stuck with no fallback — `_autostart_zone` logs `Auto-start FAILED` but doesn't attempt
anything else. A harder fallback (e.g. force-resetting the character's saved `world_tag` back
to `gs01` via a write to gamedbd's protocol) was discussed but not built — it requires writing
to live character save data, which is a meaningfully bigger risk than anything implemented so
far, and wasn't needed for either real incident this session.

### BUGFIXES (2026-07-05, same day): two real bugs found deploying the above

The login-guard mechanism above was fully implemented, deployed, and tested clean in isolation
(unit tests with mocked `GameClient`/DB), yet did *nothing* against live production traffic —
zero reaction across many real login attempts and several manually-injected synthetic ones.
Root-caused via a debug session using `py-spy dump` (inconclusive — py-spy isn't asyncio-task-
aware, only shows the OS thread parked in the event loop) and, more usefully, temporary
`_dbg()` tracing writing directly to `/tmp/login_tail_debug.log` at every decision point inside
the running process. Two independent, unrelated bugs were found and fixed:

1. **Weak-reference task GC** (`app/services/instance_watch.py`): `asyncio.create_task(coro)`
   returns a `Task` whose *only* strong reference, per the asyncio docs, is the caller's — if
   nothing holds onto the return value, the task can be garbage-collected before it ever runs,
   silently, with no exception. All three fire-and-forget spawns
   (`_maybe_autostart`'s `_autostart_zone` call, `_tail_login_log`'s `_ensure_user_zones_started`
   call, and the one-shot `_sweep_all_accounts` at watcher start) had exactly this shape. It
   "worked" for the hook-triggered path by luck — created from deep inside an already-looping
   background task, which tends to give the new task a chance to start before anything triggers
   a GC pass — but reliably failed for the one-shot startup sweep. Fixed with `_spawn()`: adds
   the task to a module-level `set` and removes it via `add_done_callback` on completion, per
   the standard asyncio-recommended pattern.
2. **Wrong gamedbd port** (the actual root cause of *this specific* feature doing nothing, even
   after fixing #1): `_ensure_user_zones_started` queried `GameClient(host="localhost",
   port=settings.server_port)` — but on the live 10.0.0.230 `.env`, `SERVER_PORT=29000`, which
   is glinkd's *client-facing* port, not gamedbd's query port (29400). Connecting to the wrong
   port fails instantly (`ConnectionRefusedError` or similar, caught inside
   `GameClient._send_packet`'s own try/except) and returns `None` → `get_user_roles()` returns
   `[]` → nothing downstream ever runs, with zero exception raised anywhere to hint at the
   problem. This is why the very first round of error-visibility improvements (throttled
   `_log_error_throttled()` calls added to every `except Exception: pass`) still showed nothing
   — there was genuinely no exception, just a fast, valid-looking empty result. Only the
   `_dbg()` trace of the actual `roles=[]` return value exposed it. Fixed by hardcoding
   `GAMEDBD_PORT = 29400` in `instance_watch.py` instead of trusting `settings.server_port`,
   which apparently means something else in practice on this deployment (worth checking
   whether `app/services/game_protocol.py`'s `get_client()` — which *does* use
   `settings.server_port` — has the same latent bug for the account pages; not investigated,
   out of scope for this session).

Both fixes verified against live production traffic after redeploy: stopped `is31` manually,
appended a synthetic `UserLogin:userid=1040` line to `authd.log` directly, watched it get
picked up within one poll cycle (~1.5s) and `is31` come back up — and separately, confirmed the
proactive startup sweep alone (no login attempt at all) brought `is31` back up within ~3
seconds of a fresh `pwadmin` restart while the watcher was left enabled.
