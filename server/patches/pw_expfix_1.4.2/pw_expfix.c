/*
 * pw_expfix.c — LD_PRELOAD patch for PW 1.4.2
 *
 * Compile: gcc -m32 -shared -fPIC -nostartfiles -o pw_expfix.so pw_expfix.c
 * Usage:   LD_PRELOAD=./pw_expfix.so ./gs gs01
 *
 * ptemplate.conf [GENERAL] keys (formula: 1 + value):
 *   exp_bonus   = 10  → 10x EXP
 *   sp_bonus    = 10  → 10x SP
 *   money_bonus = 10  → 10x coin drops from mobs
 *   drop_bonus  = 10  → 10x item drop rolls per mob kill
 *                       (applies to both element.data and extra_drops.sev drops)
 */

#include <sys/mman.h>
#include <stdint.h>
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

/* ── exp/sp stub patch ─────────────────────────────────────────────── */
#define ADJUST_STUB_ADDR     ((uint8_t *)0x080b9c04)
#define PLAYER_TEMPLATE_BASE ((char *)0x08956be0)
#define EXP_BONUS_OFFSET     0x16dc
#define SP_BONUS_OFFSET      0x16e0

static void real_adjust(int *exp_val, int *sp_val)
{
    float eb = *(float *)(PLAYER_TEMPLATE_BASE + EXP_BONUS_OFFSET);
    float sb = *(float *)(PLAYER_TEMPLATE_BASE + SP_BONUS_OFFSET);
    *exp_val = (int)(*exp_val * eb);
    *sp_val  = (int)(*sp_val  * sb);
}

/* ── item drop loop bounds (gnpc_imp::DropItemFromData) ────────────── */
/*
 * The item-roll loop runs 1x (normal) or 2x (world event flag).
 * These are 32-bit immediates inside movl instructions in the text segment.
 *   0x080b6fae: movl $1, -0x148(%ebp)   ← normal mode
 *   0x080b6fa2: movl $2, -0x148(%ebp)   ← event mode
 * The immediate is at instruction_start + 6.
 */
#define ITEM_LOOP_NORMAL_IMM  ((uint32_t *)0x080b6fb4)
#define ITEM_LOOP_EVENT_IMM   ((uint32_t *)0x080b6fa8)

/* ── money bonus +1 removal (gnpc_imp::DropItemFromData) ───────────── */
/*
 * Binary does: money * (1.0 + money_bonus). NOP fld1+faddp to get money * money_bonus.
 *   0x080b715a: d9 e8  fld1
 *   0x080b715c: de c1  faddp
 */
#define MONEY_FLD1_ADDR  ((uint8_t *)0x080b715a)

/* ── extra_drops.sev call site (gnpc_imp::DropItem at 0x080b72bd) ──── */
/*
 * gnpc_imp::DropItem calls DropItemFromGlobal exactly once per kill.
 * DropItemFromGlobal uses the drop_template system (extra_drops.sev) which
 * is the source of gold/rare item drops. Without patching this call site,
 * drop_bonus has no effect on extra_drops.sev items.
 *
 * Fix: redirect the call at 0x080b72bd to my_drop_global, which loops
 * drop_bonus times, giving gold/rare items the same multiplier as
 * element.data drops.
 *
 * Original instruction at 0x080b72bd:  E8 80 F9 FF FF  (call 0x80b6c42)
 */
#define GLOBAL_DROP_CALL_SITE ((uint8_t *)0x080b72bd)

typedef int (*drop_global_t)(void *, void *, int, int, int, int);
static const drop_global_t orig_drop_global = (drop_global_t)0x080b6c42;

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

/* ── config reader ─────────────────────────────────────────────────── */
static float read_conf(const char *key)
{
    FILE *f = fopen("/home/gamed/ptemplate.conf", "r");
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

/* ── constructor ───────────────────────────────────────────────────── */
__attribute__((constructor))
static void pw_patch(void)
{
    /* 1. Patch AdjustGlobalExpSp stub → JMP real_adjust */
    uintptr_t page = (uintptr_t)ADJUST_STUB_ADDR & ~0xffful;
    mprotect((void *)page, 0x1000, PROT_READ | PROT_WRITE | PROT_EXEC);
    int32_t rel = (int32_t)((uintptr_t)real_adjust
                            - ((uintptr_t)ADJUST_STUB_ADDR + 5));
    ADJUST_STUB_ADDR[0] = 0xE9;
    ADJUST_STUB_ADDR[1] = (uint8_t)(rel);
    ADJUST_STUB_ADDR[2] = (uint8_t)(rel >>  8);
    ADJUST_STUB_ADDR[3] = (uint8_t)(rel >> 16);
    ADJUST_STUB_ADDR[4] = (uint8_t)(rel >> 24);

    /* 2. NOP out fld1+faddp in money calculation: money*(1+bonus) → money*bonus */
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

    /* 4. Redirect DropItemFromGlobal call in DropItem → my_drop_global */
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
