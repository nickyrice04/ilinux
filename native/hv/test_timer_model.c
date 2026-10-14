/*
 * Offline model test for hv002's source-masked guest timers (private iLinux).
 *
 * test_hv_launch.py extracts the exact timer block added by
 * 0001-ilinux-hv-t6050-hv002.patch into timer_block.inc and compiles this
 * harness around it. The fake hardware keeps VM_TMR_FIQ_ENA stuck on, as the
 * H1 census found: an expired, enabled, unmasked guest timer asserts the
 * physical FIQ line. After every HV exit that line must be low (no FIQ storm),
 * and the guest must see its own view of CTL.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef uint8_t u8;
typedef uint64_t u64;

#define BIT(n)           (1ULL << (n))
#define MAX_CPUS         32
#define CNTx_CTL_ENABLE  BIT(0)
#define CNTx_CTL_IMASK   BIT(1)
#define CNTx_CTL_ISTATUS BIT(2)

enum {
    SYS_CNTV_CTL_EL0 = 1,
    SYS_CNTV_CVAL_EL0,
    SYS_CNTV_TVAL_EL0,
    SYS_CNTP_CTL_EL0,
    SYS_CNTP_CVAL_EL0,
    SYS_CNTP_TVAL_EL0,
    SYS_CNTV_CTL_EL02,
    SYS_CNTV_CVAL_EL02,
    SYS_CNTV_TVAL_EL02,
    SYS_CNTP_CTL_EL02,
    SYS_CNTP_CVAL_EL02,
    SYS_CNTP_TVAL_EL02,
};

static u64 now;
struct tmr {
    u64 ctl, cval;
} V, P;

static struct tmr *tmr_of(int r)
{
    switch (r) {
        case SYS_CNTV_CTL_EL02:
        case SYS_CNTV_CVAL_EL02:
        case SYS_CNTV_TVAL_EL02:
            return &V;
        case SYS_CNTP_CTL_EL02:
        case SYS_CNTP_CVAL_EL02:
        case SYS_CNTP_TVAL_EL02:
            return &P;
    }
    fprintf(stderr, "HV accessed a non-EL02 register %d\n", r);
    exit(2);
}

static u64 hw_read(int r)
{
    struct tmr *t = tmr_of(r);
    switch (r) {
        case SYS_CNTV_CTL_EL02:
        case SYS_CNTP_CTL_EL02: {
            u64 ctl = t->ctl & (CNTx_CTL_ENABLE | CNTx_CTL_IMASK);
            if ((t->ctl & CNTx_CTL_ENABLE) && now >= t->cval)
                ctl |= CNTx_CTL_ISTATUS;
            return ctl;
        }
        case SYS_CNTV_CVAL_EL02:
        case SYS_CNTP_CVAL_EL02:
            return t->cval;
        default:
            return t->cval - now;
    }
}

static void hw_write(int r, u64 v)
{
    struct tmr *t = tmr_of(r);
    switch (r) {
        case SYS_CNTV_CTL_EL02:
        case SYS_CNTP_CTL_EL02:
            t->ctl = v & (CNTx_CTL_ENABLE | CNTx_CTL_IMASK); /* ISTATUS is read-only */
            break;
        case SYS_CNTV_CVAL_EL02:
        case SYS_CNTP_CVAL_EL02:
            t->cval = v;
            break;
        default:
            t->cval = now + v;
    }
}

static int smp_id(void)
{
    return 0;
}

#define sr_tkn(x)     x
#define SYSREG_ISS(x) (x)
#define _mrs(r)       hw_read(r)
#define _msr(r, v)    hw_write(r, v)
#define mrs(r)        hw_read(r)
#define msr(r, v)     hw_write(r, v)

#include "timer_block.inc"

#define EXPIRED (CNTx_CTL_ENABLE | CNTx_CTL_ISTATUS)

static bool fiq_line(void)
{
    /* VM_TMR_FIQ_ENA_EL2 has ENA_V and ENA_P set and cannot be cleared. */
    return (hw_read(SYS_CNTV_CTL_EL02) & 7) == EXPIRED || (hw_read(SYS_CNTP_CTL_EL02) & 7) == EXPIRED;
}

static int failures;
#define CHECK(c)                                                                                   \
    do {                                                                                           \
        if (!(c)) {                                                                                \
            printf("FAIL line %d: %s\n", __LINE__, #c);                                            \
            failures++;                                                                            \
        }                                                                                          \
    } while (0)

/* One HV exit: hv_update_fiq's t6050 path. Returns the virtual FIQ state. */
static bool hv_exit(void)
{
    bool pending = hv_ilinux_update_timers();
    CHECK(!fiq_line());
    return pending;
}

static u64 g_rd(u64 r)
{
    u64 v = 0xdead;
    CHECK(hv_ilinux_timer_access(r, true, &v));
    return v;
}

static void g_wr(u64 r, u64 v)
{
    CHECK(hv_ilinux_timer_access(r, false, &v));
    hv_exit(); /* every trapped access ends with hv_update_fiq() */
}

struct gt {
    u64 ctl, cval, tval;
} GV = {SYS_CNTV_CTL_EL0, SYS_CNTV_CVAL_EL0, SYS_CNTV_TVAL_EL0},
  GP = {SYS_CNTP_CTL_EL0, SYS_CNTP_CVAL_EL0, SYS_CNTP_TVAL_EL0};

/* Linux arch_timer: set_next_event, then the FIQ handler's ack. */
static void arm(struct gt *g, u64 delta)
{
    u64 ctl = g_rd(g->ctl);
    g_wr(g->cval, now + delta);
    g_wr(g->ctl, (ctl | CNTx_CTL_ENABLE) & ~CNTx_CTL_IMASK);
}

static bool guest_sees_firing(struct gt *g)
{
    return (g_rd(g->ctl) & 7) == EXPIRED;
}

static void ack(struct gt *g)
{
    g_wr(g->ctl, g_rd(g->ctl) | CNTx_CTL_IMASK);
}

int main(void)
{
    /* Handoff state seen by the census: enabled, masked, expired (ctl=7). */
    V = (struct tmr){CNTx_CTL_ENABLE | CNTx_CTL_IMASK, 0};
    P = V;
    now = 1000;
    CHECK((hw_read(SYS_CNTV_CTL_EL02) & 7) == 7);
    hv_ilinux_timers_reset();
    CHECK(hw_read(SYS_CNTV_CTL_EL02) == 0 && hw_read(SYS_CNTP_CTL_EL02) == 0);
    CHECK(!hv_exit());

    /* 1. Arm, expire, deliver, ack, re-arm (virtual timer, as Linux at EL1). */
    arm(&GV, 10);
    CHECK(!hv_exit());
    now += 10;
    CHECK(fiq_line()); /* physical FIQ until the HV runs */
    CHECK(hv_exit());  /* masked at source, virtual FIQ pending */
    CHECK(guest_sees_firing(&GV));
    ack(&GV);
    CHECK(!hv_exit());
    CHECK(g_rd(GV.ctl) & CNTx_CTL_IMASK); /* the guest's own mask is visible */
    arm(&GV, 10);
    CHECK(!hv_exit());
    now += 10;
    CHECK(hv_exit());

    /* 2. Re-arm through CVAL only while the HV holds the mask. */
    g_wr(GV.cval, now + 5);
    CHECK(!hv_exit());
    CHECK(!(g_rd(GV.ctl) & CNTx_CTL_IMASK));
    now += 5;
    CHECK(hv_exit());

    /* 3. Re-arm through TVAL. */
    g_wr(GV.tval, 7);
    CHECK(!hv_exit());
    now += 7;
    CHECK(hv_exit() && guest_sees_firing(&GV));

    /* 4. CVAL into the past while masked: fires again at once, still no storm. */
    g_wr(GV.cval, now - 1);
    CHECK(hv_exit());

    /* 5. The guest disables the timer while the HV holds the mask. */
    g_wr(GV.ctl, 0);
    CHECK(!hv_exit());

    /* 6. A guest-masked expiry is not pending and stays masked. */
    g_wr(GV.cval, now);
    g_wr(GV.ctl, CNTx_CTL_ENABLE | CNTx_CTL_IMASK);
    CHECK(!hv_exit());
    CHECK((g_rd(GV.ctl) & 7) == 7);

    /* 7. Physical timer, and both timers at once. */
    arm(&GV, 3);
    arm(&GP, 4);
    now += 4;
    CHECK(hv_exit());
    CHECK(guest_sees_firing(&GV) && guest_sees_firing(&GP));
    ack(&GV);
    CHECK(hv_exit()); /* physical timer still pending */
    ack(&GP);
    CHECK(!hv_exit());

    /* 8. The counter steps back while masked: restore the guest's view. */
    arm(&GV, 2);
    now += 2;
    CHECK(hv_exit());
    now -= 5;
    CHECK(!hv_exit());
    CHECK(!(hw_read(SYS_CNTV_CTL_EL02) & CNTx_CTL_IMASK));
    now += 5;
    CHECK(fiq_line());
    CHECK(hv_exit());

    /* Non-timer registers are not claimed by the handler. */
    u64 v = 0;
    CHECK(!hv_ilinux_timer_access(0x7fff, true, &v));

    if (failures) {
        printf("timer model: %d failure(s)\n", failures);
        return 1;
    }
    printf("timer model PASS\n");
    return 0;
}
