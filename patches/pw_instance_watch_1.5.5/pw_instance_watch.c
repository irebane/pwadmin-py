/*
 * pw_instance_watch.c — LD_PRELOAD probe for PW 1.5.5 (10.0.0.230) gs01
 *
 * Compile: gcc -m32 -shared -fPIC -nostartfiles -o pw_instance_watch.so pw_instance_watch.c
 * Usage:   LD_PRELOAD="./pw_expfix_155.so ./pw_instance_watch.so" ./gs gs01 gs.conf gmserver.conf gsalias.conf is61
 *
 * Purpose: observe every call to world_manager::PlaneSwitch(gplayer_imp*, A3DVECTOR const&,
 * int, instance_key const&, unsigned int) — the single, non-virtual, base-class function that
 * handles a player's zone-switch request (walking through a portal, using a teleport item,
 * etc). Its 3rd argument is a plain `int` world tag, directly compared against
 * `world_manager::_world_tag` in the disassembly — no need to parse the `instance_key` struct
 * at all. Logs every call's arguments to /tmp/pw_switch_watch.log. Purely observational: does
 * not alter behavior.
 *
 * (Earlier attempts hooked instance_world_manager::HandleSwitchRequest and
 * global_world_manager::HandleSwitchRequest -- both installed correctly, verified against live
 * process memory, but neither fired for a real is02 entry. Those are virtual per-subclass
 * overrides; PlaneSwitch is the single common caller above them, so it's the right place.)
 *
 * How the hook works: rather than hardcoding the target's prologue bytes (which differ between
 * functions -- an earlier version got this wrong by assuming all target functions shared one
 * prologue shape), the constructor reads the *actual* live bytes at the hook address before
 * patching anything, and the trampoline replays exactly those, whatever they are. This only
 * requires knowing STOLEN_LEN (verified via `objdump -d -C` to fall on a real instruction
 * boundary -- for PlaneSwitch, "push %ebp; mov %esp,%ebp; push %edi; push %esi" = 5 bytes,
 * landing exactly before "sub $0x90,%esp").
 *
 * Stack layout at hook entry (matches original function's own entry, since we arrive via JMP,
 * not CALL, so nothing extra is pushed):
 *   [esp+0x00] return address
 *   [esp+0x04] this (world_manager*)
 *   [esp+0x08] gplayer_imp* (the player)
 *   [esp+0x0c] A3DVECTOR const* (target position)
 *   [esp+0x10] int (world tag being requested -- the value we actually care about)
 *   [esp+0x14] instance_key const*
 *   [esp+0x18] unsigned int (a flag / cost, e.g. teleport fee)
 *
 * Log rotation: the log file is owned by whatever user runs gs01 (root, via start.sh/systemd),
 * while pwadmin-py's watcher (app/services/instance_watch.py) that tails this file runs as
 * www-data and only ever needs read access. Rather than grant www-data write/sudo access to a
 * root-owned file just to truncate it, rotation is self-contained here: before each write, if
 * the file has grown past MAX_LOG_BYTES, reopen in "w" mode (truncate) instead of "a" (append)
 * for that one write. No cross-process permissions needed.
 */

#include <sys/mman.h>
#include <sys/stat.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <time.h>

#define MAX_STOLEN 16
#define LOG_PATH "/tmp/pw_switch_watch.log"
#define MAX_LOG_BYTES (5 * 1024 * 1024)

struct hook_target {
    const char *tag;
    uint8_t    *hook_addr;
    int         stolen_len;   /* must be >=5, verified via objdump to land on an insn boundary */
};

static struct hook_target HOOKS[] = {
    { "PlaneSwitch", (uint8_t *)0x081bef10, 5 },
};

static const char *g_current_tag = "?";

void log_switch_request(uint32_t this_ptr, uint32_t player, uint32_t pos,
                         uint32_t worldtag, uint32_t ikey_ptr, uint32_t flag)
{
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);

    const char *mode = "a";
    struct stat st;
    if (stat(LOG_PATH, &st) == 0 && st.st_size > MAX_LOG_BYTES)
        mode = "w";  /* rotate: this write truncates instead of appending */

    FILE *f = fopen(LOG_PATH, mode);
    if (!f) return;

    fprintf(f, "%ld.%09ld [%s] this=%08x player=%08x pos=%08x worldtag=%u ikey_ptr=%08x flag=%u ikey_bytes=",
            (long)ts.tv_sec, ts.tv_nsec, g_current_tag, this_ptr, player, pos, worldtag, ikey_ptr, flag);

    if (ikey_ptr) {
        const uint8_t *p = (const uint8_t *)(uintptr_t)ikey_ptr;
        for (int i = 0; i < 32; i++)
            fprintf(f, "%02x", p[i]);
    }
    fprintf(f, "\n");
    fclose(f);
}

/*
 * Trampoline layout, built dynamically per hook (lengths vary with stolen_len):
 *   +0x00  C7 05 <&g_current_tag> <tag>    mov $tag, g_current_tag        (10 bytes)
 *   +0x0a  FF 74 24 18   x6                pushl 0x18(%esp), 6 times      (24 bytes)
 *   +0x22  E8 <rel32>                      call log_switch_request        (5 bytes)
 *   +0x27  83 C4 18                        addl $0x18,%esp                (3 bytes)
 *   +0x2a  <stolen_len bytes verbatim, copied live from the real target>
 *   +0x2a+stolen_len  E9 <rel32>           jmp hook_addr+stolen_len       (5 bytes)
 */
#define SETTAG_LEN   10
#define PUSHES_LEN   24
#define CALL_OFF     (SETTAG_LEN + PUSHES_LEN)          /* 0x22 */
#define CLEANUP_OFF  (CALL_OFF + 5)                     /* 0x27 */
#define STOLEN_OFF   (CLEANUP_OFF + 3)                  /* 0x2a */

static void install_one_hook(struct hook_target *t)
{
    if (t->stolen_len < 5 || t->stolen_len > MAX_STOLEN) return;

    int jmp_off = STOLEN_OFF + t->stolen_len;
    int total_len = jmp_off + 5;

    uint8_t *tramp = mmap(NULL, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC,
                           MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (tramp == MAP_FAILED) return;

    /* mov $t->tag, g_current_tag */
    tramp[0] = 0xC7;
    tramp[1] = 0x05;
    uint32_t gtag_addr = (uint32_t)(uintptr_t)&g_current_tag;
    uint32_t tag_val   = (uint32_t)(uintptr_t)t->tag;
    memcpy(tramp + 2, &gtag_addr, 4);
    memcpy(tramp + 6, &tag_val, 4);

    /* 6x pushl 0x18(%esp) */
    for (int i = 0; i < 6; i++) {
        uint8_t *p = tramp + SETTAG_LEN + i * 4;
        p[0] = 0xFF; p[1] = 0x74; p[2] = 0x24; p[3] = 0x18;
    }

    /* call log_switch_request */
    tramp[CALL_OFF] = 0xE8;
    int32_t call_rel = (int32_t)((uintptr_t)log_switch_request
                                  - ((uintptr_t)(tramp + CALL_OFF) + 5));
    memcpy(tramp + CALL_OFF + 1, &call_rel, 4);

    /* addl $0x18,%esp */
    tramp[CLEANUP_OFF] = 0x83; tramp[CLEANUP_OFF + 1] = 0xC4; tramp[CLEANUP_OFF + 2] = 0x18;

    /* copy the real, live original bytes -- read BEFORE we touch the target at all */
    memcpy(tramp + STOLEN_OFF, t->hook_addr, t->stolen_len);

    /* jmp back to hook_addr + stolen_len */
    uint8_t *resume_addr = t->hook_addr + t->stolen_len;
    tramp[jmp_off] = 0xE9;
    int32_t jmp_rel = (int32_t)((uintptr_t)resume_addr - ((uintptr_t)(tramp + jmp_off) + 5));
    memcpy(tramp + jmp_off + 1, &jmp_rel, 4);

    (void)total_len; /* just for documentation/clarity of the layout above */

    /* now patch the real target's first 5 bytes with a JMP into our trampoline */
    uintptr_t page = (uintptr_t)t->hook_addr & ~0xffful;
    mprotect((void *)page, 0x2000, PROT_READ | PROT_WRITE | PROT_EXEC);

    int32_t hook_rel = (int32_t)((uintptr_t)tramp - ((uintptr_t)t->hook_addr + 5));
    t->hook_addr[0] = 0xE9;
    memcpy(t->hook_addr + 1, &hook_rel, 4);
}

__attribute__((constructor))
static void install_hook(void)
{
    for (unsigned i = 0; i < sizeof(HOOKS) / sizeof(HOOKS[0]); i++)
        install_one_hook(&HOOKS[i]);
}
