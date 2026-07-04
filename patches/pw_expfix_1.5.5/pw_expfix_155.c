/*
 * pw_expfix_155.c — LD_PRELOAD patch for PW 1.5.5 (10.0.0.230)
 *
 * Compile: gcc -m32 -shared -fPIC -nostartfiles -o pw_expfix_155.so pw_expfix_155.c
 * Usage:   LD_PRELOAD=./pw_expfix_155.so ./gs gs01 gs.conf gmserver.conf gsalias.conf is61
 *
 * Same problem as PW 1.4.2 (see pw_expfix.c on the .240 server): the shipped gs binary
 * has real getter/hook points for rate bonuses, but several are dead stubs that never
 * apply the configured multiplier. Verified by disassembly (objdump -d -C) against
 * /home/gamed/gs (ELF 32-bit, not stripped, has full symbol names):
 *
 *   - player_template::AdjustGlobalExpSp(int&,int&) @ 0x08105bf2 is called once, from
 *     gnpc_imp::DispatchExp (the real per-kill exp/sp distribution code), but its body
 *     is literally `push ebp; mov esp,ebp; leave; ret` -- a no-op. exp_bonus/sp_bonus in
 *     ptemplate.conf's [GENERAL] section are silently ignored no matter what they say.
 *   - player_template::GetGlobalMoneyBonus(float*) @ 0x08105bf8 DOES work (reads a live
 *     singleton field), and gnpc_imp::DropItemFromData applies it as money*(1.0+bonus)
 *     -- so money_bonus=10 actually yields 11x, not 10x. We NOP the "+1" for parity with
 *     the documented ptemplate.conf semantics (bonus IS the multiplier).
 *   - drop_bonus has no support at all in this binary (no such string, no such field) --
 *     same situation as 1.4.2 before pw_expfix.c. We replicate the same technique:
 *     patch the item-roll loop bound in DropItemFromData, and wrap the DropItemFromGlobal
 *     call site in DropItem so it loops drop_bonus times (covers extra_drops.sev drops).
 *
 * ptemplate.conf [GENERAL] keys read by this patch (formula: value IS the multiplier):
 *   exp_bonus   = 10  -> 10x EXP
 *   sp_bonus    = 100 -> 100x SP
 *   money_bonus = 10  -> 10x coin drops (was 11x before this patch's NOP fix)
 *   drop_bonus  = N   -> N item/gold drop rolls per mob kill
 */

#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define PTEMPLATE_PATH "/home/gamed/ptemplate.conf"

/* ── exp/sp stub patch: player_template::AdjustGlobalExpSp(int&, int&) ────── */
#define ADJUST_STUB_ADDR ((uint8_t *)0x08105bf2)

static float g_exp_bonus = 1.0f;
static float g_sp_bonus  = 1.0f;

static void real_adjust(int *exp_val, int *sp_val)
{
    *exp_val = (int)(*exp_val * g_exp_bonus);
    *sp_val  = (int)(*sp_val  * g_sp_bonus);
}

/* ── money bonus +1 removal (gnpc_imp::DropItemFromData) ───────────────────── */
/*
 * money * (1.0 + money_bonus) -> money * money_bonus. Sequence is:
 *   0x08102123: d9 e8  fld1
 *   0x08102125: de c1  faddp
 */
#define MONEY_FLD1_ADDR ((uint8_t *)0x08102123)

/* ── item drop loop bounds (gnpc_imp::DropItemFromData) ─────────────────────── */
/*
 * The item-roll loop runs 1x (normal) or 2x (world event flag), set via:
 *   0x08101f4d: movl $2, -0x148(%ebp)   <- event mode (immediate @ +6 = 0x08101f53)
 *   0x08101f59: movl $1, -0x148(%ebp)   <- normal mode (immediate @ +6 = 0x08101f5f)
 */
#define ITEM_LOOP_EVENT_IMM  ((uint32_t *)0x08101f53)
#define ITEM_LOOP_NORMAL_IMM ((uint32_t *)0x08101f5f)

/* ── extra_drops.sev call site (gnpc_imp::DropItem @ 0x08102287) ────────────── */
/*
 * gnpc_imp::DropItem calls DropItemFromGlobal exactly once per kill. Without patching
 * this call site, drop_bonus has no effect on extra_drops.sev (gold/rare item) drops.
 * Original instruction at 0x08102287: E8 3e f9 ff ff  (call 0x08101bca)
 */
#define GLOBAL_DROP_CALL_SITE ((uint8_t *)0x08102287)

typedef int (*drop_global_t)(void *, void *, int, int, int, int);
static const drop_global_t orig_drop_global = (drop_global_t)0x08101bca;

static uint32_t g_drop_bonus = 1;

static int __attribute__((noinline))
my_drop_global(void *self, void *xid, int a, int b, int c, int d)
{
    int ret = 1;
    uint32_t i;
    for (i = 0; i < g_drop_bonus; i++)
        ret = orig_drop_global(self, xid, a, b, c, d);
    return ret;
}

/* ── config reader ───────────────────────────────────────────────────────── */
static float read_conf(const char *key)
{
    FILE *f = fopen(PTEMPLATE_PATH, "r");
    if (!f) return 0.0f;
    char line[256];
    size_t klen = strlen(key);
    float val = 0.0f;
    while (fgets(line, sizeof(line), f)) {
        char *p = line;
        while (*p == ' ' || *p == '\t') p++;
        if (strncmp(p, key, klen) == 0) {
            p += klen;
            while (*p == ' ' || *p == '\t' || *p == '=') p++;
            val = strtof(p, NULL);
            break;
        }
    }
    fclose(f);
    return val;
}

/* ── constructor ─────────────────────────────────────────────────────────── */
__attribute__((constructor))
static void pw_patch(void)
{
    float eb = read_conf("exp_bonus");
    float sb = read_conf("sp_bonus");
    g_exp_bonus = (eb > 0.0f) ? eb : 1.0f;
    g_sp_bonus  = (sb > 0.0f) ? sb : 1.0f;

    /* 1. Patch AdjustGlobalExpSp stub -> JMP real_adjust */
    uintptr_t page = (uintptr_t)ADJUST_STUB_ADDR & ~0xffful;
    mprotect((void *)page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    int32_t rel = (int32_t)((uintptr_t)real_adjust
                            - ((uintptr_t)ADJUST_STUB_ADDR + 5));
    ADJUST_STUB_ADDR[0] = 0xE9;
    ADJUST_STUB_ADDR[1] = (uint8_t)(rel);
    ADJUST_STUB_ADDR[2] = (uint8_t)(rel >>  8);
    ADJUST_STUB_ADDR[3] = (uint8_t)(rel >> 16);
    ADJUST_STUB_ADDR[4] = (uint8_t)(rel >> 24);

    /* 2. NOP out fld1+faddp in money calculation: money*(1+bonus) -> money*bonus */
    uintptr_t money_page = (uintptr_t)MONEY_FLD1_ADDR & ~0xffful;
    mprotect((void *)money_page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    MONEY_FLD1_ADDR[0] = 0x90;
    MONEY_FLD1_ADDR[1] = 0x90;
    MONEY_FLD1_ADDR[2] = 0x90;
    MONEY_FLD1_ADDR[3] = 0x90;

    float drop_bonus = read_conf("drop_bonus");
    if (drop_bonus <= 0.0f) return;

    g_drop_bonus = (uint32_t)drop_bonus;

    /* 3. Patch item drop loop bounds: runs drop_bonus times per kill */
    uintptr_t loop_page = (uintptr_t)ITEM_LOOP_NORMAL_IMM & ~0xffful;
    mprotect((void *)loop_page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    uint32_t normal_iters = (uint32_t)drop_bonus;
    uint32_t event_iters  = normal_iters * 2;
    memcpy(ITEM_LOOP_NORMAL_IMM, &normal_iters, 4);
    memcpy(ITEM_LOOP_EVENT_IMM,  &event_iters,  4);

    /* 4. Redirect DropItemFromGlobal call in DropItem -> my_drop_global */
    uintptr_t call_page = (uintptr_t)GLOBAL_DROP_CALL_SITE & ~0xffful;
    mprotect((void *)call_page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    int32_t grel = (int32_t)((uintptr_t)my_drop_global
                             - ((uintptr_t)GLOBAL_DROP_CALL_SITE + 5));
    GLOBAL_DROP_CALL_SITE[0] = 0xE8;
    GLOBAL_DROP_CALL_SITE[1] = (uint8_t)(grel);
    GLOBAL_DROP_CALL_SITE[2] = (uint8_t)(grel >>  8);
    GLOBAL_DROP_CALL_SITE[3] = (uint8_t)(grel >> 16);
    GLOBAL_DROP_CALL_SITE[4] = (uint8_t)(grel >> 24);
}
