/*
 * Gran Turismo (PS1, PAL SCES-00984) - overlay cheat menu.
 *
 * Resident code, copied to 0x8000F000 by the GTMENU.EXE start-up stub (src/stub.S) and kept
 * there while the game switches between GTMENU.EXE (menus) and GTMAIN.EXE (races, licences).
 * Each executable's stub calls cheat_boot(exe), which redirects three `jal` of the game:
 *
 *   pad_hook   the game's copy of the pad buffers (once per game frame): reads port 1,
 *              runs the menu while SELECT is held and hides the pad from the game meanwhile;
 *   draw_hook  the game's DrawOTag of the frame: once the GPU has drawn the frame (DrawSync),
 *              draws the menu over it with GP0 writes (TILE primitives, 5x7 font from font.py);
 *   tick_hook  (GTMAIN only) the race clock tick (+20/+40 ms per frame): skipped in a
 *              licence test while FREEZE TIMER is on, once the clock has left 0.
 *
 * The state (struct g, 0x8000FF80) lives outside the copied block so that it survives the
 * changes of executable (the FREEZE TIMER choice made in the menus applies to the licences).
 *
 * Copyright (C) 2026 soaresden - GPL-3.0-or-later.
 */
#include "font.h"
#include "exes.h"

typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;

#define MAGIC 0x31544743u            /* "CGT1": the state is initialised */
#define MONEY_MAX 99999999u          /* the game's own limit for prize money (GTMAIN 0x80021608) */
#define SHOW 8                       /* polls with SELECT held before the menu appears */
#define TAPLEN 2                     /* polls of SELECT given back to the game after a short tap */

/* pad bits once inverted (1 = pressed), as in the game's pad code */
#define B_SELECT 0x0001
#define B_UP 0x0010
#define B_RIGHT 0x0020
#define B_DOWN 0x0040
#define B_LEFT 0x0080
#define B_L1 0x0400
#define B_R1 0x0800
#define B_TRIANGLE 0x1000
#define B_CIRCLE 0x2000
#define B_CROSS 0x4000
#define B_SQUARE 0x8000

struct exe {
    u32 memcpy, drawsync, drawotag, tick, clock, money, mode;   /* game addresses (gt1cheat/exes.py) */
    u32 site[3], orig[3];                        /* the redirected jal and their original word */
};

struct g {
    u32 magic;                                   /* kept across executables: */
    u8 freeze;                                   /*   FREEZE TIMER on */
    u8 line;                                     /*   0 = FREEZE TIMER, 1 = MONEY */
    u8 step;                                     /*   money step = 10^step */
    u8 exe;                                      /* set by cheat_boot: */
    struct exe e;                                /*   the running executable (memcpy..mode) */
    u32 prev;                                    /*   buttons of the previous poll */
    u8 hold;                                     /*   polls with SELECT held (max 255) */
    u8 used;                                     /*   another button pressed during this hold */
    u8 tap;                                      /*   polls of SELECT still to give the game */
    u8 rep;                                      /*   auto-repeat of LEFT / RIGHT */
    u8 vis;                                      /*   menu shown */
    u8 shx, shy;                                 /*   font pixel = 1 << shx by 1 << shy */
};
/* the base address in a register that GCC cannot rebuild (it would redo lui/ori each time) */
static inline struct g *G_(void)
{
    struct g *g;
    __asm__("" : "=r"(g) : "0"(0x8000FF80));
    return g;
}
#define G G_()

static const struct exe EXES[2] = { EXE_MAIN, EXE_MENU };

#define GP0 (*(volatile u32 *)0x1F801810)
#define GPUSTAT (*(volatile u32 *)0x1F801814)

void pad_hook(u8 *dst, const u8 *src, int n);
void draw_hook(void *ot);
void tick_hook(void);

/* ---------------------------------------------------------------- boot */

void cheat_boot(int exe)
{
    struct g *g = G;
    const struct exe *e = &EXES[exe];
    static void *const fn[3] = { pad_hook, draw_hook, tick_hook };
    u32 *w = (u32 *)&g->e, *r = (u32 *)e;
    int i;

    for (i = 0; i < 3; i++)                       /* not the expected game: change nothing */
        if (e->site[i] && *(u32 *)e->site[i] != e->orig[i])
            return;
    if (g->magic != MAGIC) {
        g->magic = MAGIC;
        g->freeze = g->line = 0;
        g->step = 3;
    }
    for (i = 0; i < (int)(sizeof(struct exe) / 4); i++)
        w[i] = r[i];
    g->exe = exe;
    g->prev = 0;
    g->hold = g->used = g->tap = g->rep = g->vis = 0;
    for (i = 0; i < 3; i++)
        if (e->site[i])
            *(u32 *)e->site[i] = 0x0C000000 | (((u32)fn[i] >> 2) & 0x03FFFFFF);
}

/* ---------------------------------------------------------------- input */

static u32 pow10(int n)
{
    u32 v = 1;
    while (n--)
        v *= 10;
    return v;
}

static void menu(struct g *g, u32 b, u32 pr)
{
    u32 *m = (u32 *)g->e.money, v = *m, step;

    if (pr & (B_UP | B_DOWN))
        g->line ^= 1;
    if (!g->line) {
        if (pr & (B_LEFT | B_RIGHT | B_CROSS | B_CIRCLE))
            g->freeze ^= 1;
        return;
    }
    if ((pr & B_R1) && g->step < 7)
        g->step++;
    if ((pr & B_L1) && g->step)
        g->step--;
    if (v > MONEY_MAX)
        v = MONEY_MAX;
    if (pr & B_TRIANGLE)
        v = MONEY_MAX;
    if (pr & B_SQUARE)
        v = 0;
    if (b & (B_LEFT | B_RIGHT)) {
        if (pr & (B_LEFT | B_RIGHT))
            g->rep = 0;
        else if (++g->rep < 10)                   /* held: repeat every other poll after 10 */
            goto done;
        else
            g->rep = 8;
        step = pow10(g->step);
        if (b & B_RIGHT)
            v = v > MONEY_MAX - step ? MONEY_MAX : v + step;
        else
            v = v < step ? 0 : v - step;
    }
done:
    if (v != *m)
        *m = v;
}

void pad_hook(u8 *dst, const u8 *src, int n)
{
    struct g *g = G;
    u8 *p = dst;
    u32 b, pr;

    ((void (*)(u8 *, const u8 *, int))g->e.memcpy)(dst, src, n);
    if ((p[1] & 0xF0) == 0x80)                    /* multitap: its slot A */
        p += 2;
    if (p[0]) {                                   /* no pad on port 1 */
        g->hold = g->vis = 0;
        return;
    }
    b = ~(p[2] | p[3] << 8) & 0xFFFF;
    pr = b & ~g->prev;
    g->prev = b;
    if (b & B_SELECT) {
        if (g->hold < 255)
            g->hold++;
        if (b & ~B_SELECT)
            g->used = 1;
        if (g->hold >= SHOW) {
            g->vis = 1;
            menu(g, b, pr);
        }
        p[2] = p[3] = 0xFF;                       /* the game sees no button */
        return;
    }
    if (g->hold && !g->used && g->hold < SHOW)    /* a short tap: SELECT is the game's */
        g->tap = TAPLEN;
    g->hold = g->used = g->vis = 0;
    if (g->tap) {
        g->tap--;
        p[2] &= ~B_SELECT;
    }
}

/* ---------------------------------------------------------------- clock */

void tick_hook(void)
{
    struct g *g = G;

    /* game mode 4 = licence test; the clock leaves 0 first (a licence never ends otherwise) */
    if (g->freeze && *(volatile u8 *)g->e.mode == 4 && *(volatile u32 *)g->e.clock)
        return;
    ((void (*)(void))g->e.tick)();
}

/* ---------------------------------------------------------------- drawing */

static void gp0(u32 w)
{
    while (!(GPUSTAT & 0x04000000))
        ;
    GP0 = w;
}

static void rect(struct g *g, int x, int y, int w, int h, u32 cmd)
{
    gp0(cmd);
    GP0 = (u32)(y << g->shy) << 16 | (u32)(x << g->shx);
    GP0 = (u32)(h << g->shy) << 16 | (u32)(w << g->shx);
}

static int text(struct g *g, int x, int y, const u8 *str, u32 col)
{
    for (; *str != 0xFF; str++, x += 6) {
        const u8 *f = FONT + *str * 5;
        int c, r;
        for (c = 0; c < 5; c++)
            for (r = 0; r < 7; r++)
                if (f[c] >> r & 1)
                    rect(g, x + c, y + r, 1, 1, col);
    }
    return x + 6;
}

static void number(struct g *g, int x, int y, u32 v, u32 col, int plus)
{
    u8 buf[16];
    int i = 15, n = 0;

    buf[15] = 0xFF;
    do {
        if (n == 3) {
            buf[--i] = G_COMMA;
            n = 0;
        }
        buf[--i] = v % 10;
        v /= 10;
        n++;
    } while (v);
    if (plus)
        buf[--i] = G_PLUS;
    text(g, x, y, buf + i, col);
}

#define WHITE 0x60FFFFFF
#define GREY 0x60A0A0A0
#define YELLOW 0x6000FFFF                         /* GPU colours are 0xBBGGRR */
#define CYAN 0x60FFE040
#define PW 116                                    /* panel, in font pixels */
#define PH 41

void draw_hook(void *ot)
{
    struct g *g = G;
    u32 stat, c1, c2;
    int x, y;

    ((void (*)(void *))g->e.drawotag)(ot);
    if (!g->vis)
        return;
    ((int (*)(int))g->e.drawsync)(0);             /* the frame is drawn: the menu goes over it */
    stat = GPUSTAT;
    g->shx = (stat >> 18) & 1;                    /* 512 / 640 wide: 2 GPU pixels per font pixel */
    g->shy = (stat >> 19) & 1;                    /* 480 lines */
    x = (stat & 0x10000) ? 368 : (stat >> 17) & 1 ? 320 : 256;   /* width in font pixels */
    x = (x - PW) / 2;
    y = 30;

    gp0(0xE1000000 | (stat & 0x79F) | 0x400);     /* semi-transparency 0 (B/2 + F/2), draw everywhere */
    gp0(0xE6000000);                              /* no mask bit */
    rect(g, x, y, PW, PH, 0x62000000);            /* half-dark panel */

    c1 = g->line ? WHITE : YELLOW;
    c2 = g->line ? YELLOW : WHITE;
    text(g, x + 10, y + 3, S_TITLE, CYAN);
    text(g, x + 4, y + 12 + 9 * g->line, S_ARROW, YELLOW);
    text(g, text(g, x + 10, y + 12, S_FREEZE, c1), y + 12, g->freeze ? S_ON : S_OFF, c1);
    number(g, text(g, x + 10, y + 21, S_MONEY, c2), y + 21, *(u32 *)g->e.money, c2, 0);
    number(g, text(g, x + 10, y + 30, S_STEP, GREY), y + 30, pow10(g->step), GREY, 1);

    gp0(0xE1000000 | (stat & 0x7FF) | ((stat >> 4) & 0x800));   /* the game's draw mode again */
    gp0(0xE6000000 | ((stat >> 11) & 3));
}
