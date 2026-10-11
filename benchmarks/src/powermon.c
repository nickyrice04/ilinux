// powermon.c - read-only energy / DVFS sampler for Apple Silicon macOS,
// no root required.  Uses the IOReport library (private, read-only API, the
// same interface open-source monitors such as macmon use) to read the
// "Energy Model" channels (energy counters per block) and the CPU/GPU
// performance-state residency channels.
//
//   clang -O2 powermon.c -o powermon -framework CoreFoundation -ldl
//   powermon [-i ms] [-n samples] [-- cmd args...]
//
// With a command: samples continuously while the command runs and prints the
// energy consumed per channel (J), average power (W) and per-cluster
// frequency-state residency for the run.  Without a command: prints channel
// names once (discovery) and exits.  Output is JSON lines.
#include <CoreFoundation/CoreFoundation.h>
#include <dlfcn.h>
#include <spawn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

extern char **environ;

typedef struct IOReportSubscription *IOReportSubscriptionRef;
typedef CFDictionaryRef (*CopyChannelsInGroup_t)(CFStringRef, CFStringRef, uint64_t, uint64_t, uint64_t);
typedef void (*MergeChannels_t)(CFDictionaryRef, CFDictionaryRef, CFTypeRef);
typedef IOReportSubscriptionRef (*CreateSubscription_t)(void *, CFMutableDictionaryRef, CFMutableDictionaryRef *, uint64_t, CFTypeRef);
typedef CFDictionaryRef (*CreateSamples_t)(IOReportSubscriptionRef, CFMutableDictionaryRef, CFTypeRef);
typedef CFDictionaryRef (*CreateSamplesDelta_t)(CFDictionaryRef, CFDictionaryRef, CFTypeRef);
typedef int64_t (*SimpleGetIntegerValue_t)(CFDictionaryRef, int32_t);
typedef CFStringRef (*ChannelGetStr_t)(CFDictionaryRef);
typedef int32_t (*StateGetCount_t)(CFDictionaryRef);
typedef CFStringRef (*StateGetNameForIndex_t)(CFDictionaryRef, int32_t);
typedef int64_t (*StateGetResidency_t)(CFDictionaryRef, int32_t);

static CopyChannelsInGroup_t pCopyChannelsInGroup;
static MergeChannels_t pMergeChannels;
static CreateSubscription_t pCreateSubscription;
static CreateSamples_t pCreateSamples;
static CreateSamplesDelta_t pCreateSamplesDelta;
static SimpleGetIntegerValue_t pSimpleGetIntegerValue;
static ChannelGetStr_t pGetGroup, pGetSubGroup, pGetName, pGetUnit;
static StateGetCount_t pStateGetCount;
static StateGetNameForIndex_t pStateGetName;
static StateGetResidency_t pStateGetResidency;

static int load(void) {
    void *h = dlopen("/usr/lib/libIOReport.dylib", RTLD_NOW);
    if (!h) { fprintf(stderr, "powermon: cannot load libIOReport: %s\n", dlerror()); return -1; }
#define L(var, sym) if (!(var = dlsym(h, sym))) { fprintf(stderr, "powermon: missing %s\n", sym); return -1; }
    L(pCopyChannelsInGroup, "IOReportCopyChannelsInGroup")
    L(pMergeChannels, "IOReportMergeChannels")
    L(pCreateSubscription, "IOReportCreateSubscription")
    L(pCreateSamples, "IOReportCreateSamples")
    L(pCreateSamplesDelta, "IOReportCreateSamplesDelta")
    L(pSimpleGetIntegerValue, "IOReportSimpleGetIntegerValue")
    L(pGetGroup, "IOReportChannelGetGroup")
    L(pGetSubGroup, "IOReportChannelGetSubGroup")
    L(pGetName, "IOReportChannelGetChannelName")
    L(pGetUnit, "IOReportChannelGetUnitLabel")
    L(pStateGetCount, "IOReportStateGetCount")
    L(pStateGetName, "IOReportStateGetNameForIndex")
    L(pStateGetResidency, "IOReportStateGetResidency")
#undef L
    return 0;
}

static void cfstr(CFStringRef s, char *buf, size_t n) {
    buf[0] = 0;
    if (s) CFStringGetCString(s, buf, (CFIndex)n, kCFStringEncodingUTF8);
}

static double now(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec * 1e-9;
}

// Accumulators keyed by channel label.
#define MAXCH 512
static char ch_name[MAXCH][160];
static double ch_val[MAXCH];
static int nch;
static double *slot(const char *name) {
    for (int i = 0; i < nch; i++) if (!strcmp(ch_name[i], name)) return &ch_val[i];
    if (nch == MAXCH) return NULL;
    snprintf(ch_name[nch], sizeof ch_name[nch], "%s", name);
    ch_val[nch] = 0;
    return &ch_val[nch++];
}

static double unit_to_joules(const char *unit) {
    if (!strcmp(unit, "mJ")) return 1e-3;
    if (!strcmp(unit, "uJ")) return 1e-6;
    if (!strcmp(unit, "nJ")) return 1e-9;
    return 0;  // not an energy channel
}

static void accumulate(CFDictionaryRef delta, int discovery) {
    CFArrayRef arr = CFDictionaryGetValue(delta, CFSTR("IOReportChannels"));
    if (!arr) return;
    for (CFIndex i = 0; i < CFArrayGetCount(arr); i++) {
        CFDictionaryRef ch = CFArrayGetValueAtIndex(arr, i);
        char g[64], sg[96], n[96], u[16], key[160];
        cfstr(pGetGroup(ch), g, sizeof g);
        cfstr(pGetSubGroup(ch), sg, sizeof sg);
        cfstr(pGetName(ch), n, sizeof n);
        cfstr(pGetUnit(ch), u, sizeof u);
        if (!strcmp(g, "Energy Model")) {
            double scale = unit_to_joules(u);
            if (discovery) { printf("{\"group\":\"%s\",\"channel\":\"%s\",\"unit\":\"%s\"}\n", g, n, u); continue; }
            if (scale == 0) continue;
            snprintf(key, sizeof key, "energy_J:%s", n);
            double *p = slot(key);
            if (p) *p += pSimpleGetIntegerValue(ch, 0) * scale;
        } else {  // performance-state residency channels
            int cnt = pStateGetCount(ch);
            if (discovery) {
                printf("{\"group\":\"%s\",\"subgroup\":\"%s\",\"channel\":\"%s\",\"states\":%d}\n", g, sg, n, cnt);
                continue;
            }
            if (strcmp(sg, "CPU Core Performance States") && strcmp(sg, "GPU Performance States")) continue;
            for (int s = 0; s < cnt; s++) {
                char st[64];
                cfstr(pStateGetName(ch, s), st, sizeof st);
                snprintf(key, sizeof key, "residency:%s:%s", n, st);
                double *p = slot(key);
                if (p) *p += (double)pStateGetResidency(ch, s);
            }
        }
    }
}

int main(int argc, char **argv) {
    int interval_ms = 200, cmd_at = -1;
    for (int i = 1; i < argc; i++) {
        if (!strcmp(argv[i], "-i") && i + 1 < argc) interval_ms = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--")) { cmd_at = i + 1; break; }
    }
    if (load()) return 1;
    CFDictionaryRef energy = pCopyChannelsInGroup(CFSTR("Energy Model"), NULL, 0, 0, 0);
    CFDictionaryRef cpu = pCopyChannelsInGroup(CFSTR("CPU Stats"), CFSTR("CPU Core Performance States"), 0, 0, 0);
    CFDictionaryRef gpu = pCopyChannelsInGroup(CFSTR("GPU Stats"), CFSTR("GPU Performance States"), 0, 0, 0);
    if (!energy) { fprintf(stderr, "powermon: no Energy Model channels\n"); return 1; }
    CFMutableDictionaryRef want = CFDictionaryCreateMutableCopy(kCFAllocatorDefault, 0, energy);
    if (cpu) pMergeChannels(want, cpu, NULL);
    if (gpu) pMergeChannels(want, gpu, NULL);
    CFMutableDictionaryRef subbed = NULL;
    IOReportSubscriptionRef sub = pCreateSubscription(NULL, want, &subbed, 0, NULL);
    if (!sub) { fprintf(stderr, "powermon: subscription failed\n"); return 1; }

    if (cmd_at < 0 || cmd_at >= argc) {  // discovery mode
        CFDictionaryRef a = pCreateSamples(sub, subbed, NULL);
        usleep(100000);
        CFDictionaryRef b = pCreateSamples(sub, subbed, NULL);
        CFDictionaryRef d = pCreateSamplesDelta(a, b, NULL);
        accumulate(d, 1);
        return 0;
    }

    pid_t pid;
    CFDictionaryRef prev = pCreateSamples(sub, subbed, NULL);
    double t0 = now();
    if (posix_spawnp(&pid, argv[cmd_at], NULL, NULL, &argv[cmd_at], environ) != 0) {
        perror("posix_spawnp");
        return 1;
    }
    int status = 0, done = 0;
    while (!done) {
        usleep(interval_ms * 1000);
        if (waitpid(pid, &status, WNOHANG) == pid) done = 1;
        CFDictionaryRef cur = pCreateSamples(sub, subbed, NULL);
        CFDictionaryRef d = pCreateSamplesDelta(prev, cur, NULL);
        accumulate(d, 0);
        CFRelease(d);
        CFRelease(prev);
        prev = cur;
    }
    double dt = now() - t0;
    printf("{\"bench\":\"power\",\"seconds\":%.3f,\"exit\":%d", dt, WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    for (int i = 0; i < nch; i++) {
        if (!strncmp(ch_name[i], "energy_J:", 9)) {
            if (ch_val[i] <= 0) continue;
            printf(",\"%s\":%.4f,\"avgW:%s\":%.3f", ch_name[i], ch_val[i], ch_name[i] + 9, ch_val[i] / dt);
        }
    }
    printf("}\n");
    // Residency summary: fraction of time per state for each CPU/GPU channel.
    for (int i = 0; i < nch; i++) {
        if (strncmp(ch_name[i], "residency:", 10) || ch_val[i] <= 0) continue;
        printf("{\"bench\":\"power-residency\",\"key\":\"%s\",\"ticks\":%.0f}\n", ch_name[i] + 10, ch_val[i]);
    }
    return 0;
}
