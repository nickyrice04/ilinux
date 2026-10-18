// bulk-log-reader.m: read-only reader for the M5's bulk-only kernel-log USB function.
//
// boot039's Stage-B init (and later the RAM root) presents one vendor-class interface
// (class 0xff, number 0) with one bulk-IN and one bulk-OUT endpoint and no interrupt
// endpoint. No macOS driver binds it. This tool opens that interface from user space
// and copies the bulk-IN data into a file. Contract (tools/m1n1-client/bulk-log-reader-brief.md):
//   * the identity is fixed in this source; no option names a vendor, product, bcdDevice
//     or endpoint, so the tool cannot be pointed at m1n1 or at any other device;
//   * it opens the interface only (never the device), copies the IN pipe only, and apart
//     from the IN tokens of its read requests it sends the device nothing;
//   * it never retries an open and never re-opens after a stop.
// test_bulk_log_reader.py checks this source for forbidden calls.
//
// Build: clang -fobjc-arc -O2 -Wall -Wextra -framework Foundation -framework IOKit \
//          -framework IOUSBHost -o build/control/bulk-log-reader tools/m1n1-client/bulk-log-reader.m
// Usage: bulk-log-reader --out FILE [--port N] [--wait 120] [--seconds 600] [--dry-run]
// Exit:  0 done (data arrived); 2 nothing matched; 3 open failed; 4 identity mismatch;
//        5 stalled, device gone without data, repeated errors or oversize; 6 refused or disk error.

#import <Foundation/Foundation.h>
#import <IOKit/IOKitLib.h>
#import <IOKit/IOMessage.h>
#import <IOKit/usb/IOUSBHostFamilyDefinitions.h>
#import <IOUSBHost/IOUSBHost.h>
#include <errno.h>
#include <fcntl.h>
#include <mach/mach_time.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/sysctl.h>
#include <sys/time.h>
#include <unistd.h>

// The fixed identity: VID:PID 1d6b:0104, interface 0 of configuration 1, class 0xff.
enum { kVendor = 0x1d6b, kProduct = 0x0104, kInterfaceNumber = 0, kConfigValue = 1, kVendorClass = 0xff };
// bcdDevice per stage, a fixed two-entry table: boot039's Stage-B init, then the RAM root.
static const unsigned kStageBcd[2] = { 0x0139, 0x0039 };
static const char *const kStageName[2] = { "boot039 Stage-B init", "RAM root" };
static NSString *const kProductPrefix = @"iLinux J716c control channel, port ";

#define READ_CAPACITY 16384            // a multiple of 512
#define READ_TIMEOUT 5.0               // seconds per request
#define MAX_SECONDS_ALLOWED 3600
#define MAX_CAPTURE (64ULL << 20)
#define LOCK_PATH "build/native-intake/bulk-log-reader.lock"

static volatile sig_atomic_t g_stop;        // SIGINT or SIGTERM
static volatile sig_atomic_t g_terminated;  // the interface service went away
static int g_side = -1;                     // sidecar file
static double g_t0;                         // monotonic start
static int g_lock = -1;

static double mono(void)
{
    static mach_timebase_info_data_t tb;
    if (!tb.denom) mach_timebase_info(&tb);
    return (double)mach_absolute_time() * tb.numer / tb.denom / 1e9;
}

static void utc(char *out, size_t n)
{
    struct timeval tv;
    gettimeofday(&tv, NULL);
    struct tm tm;
    gmtime_r(&tv.tv_sec, &tm);
    size_t k = strftime(out, n, "%Y-%m-%dT%H:%M:%S", &tm);
    snprintf(out + k, n - k, ".%03dZ", (int)(tv.tv_usec / 1000));
}

// One sidecar line (UTC time, seconds since start, text); also on stdout.
static void side(const char *fmt, ...)
{
    char ts[40], body[900], line[1000];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(body, sizeof body, fmt, ap);
    va_end(ap);
    utc(ts, sizeof ts);
    int n = snprintf(line, sizeof line, "%s t+%.1fs %s\n", ts, g_t0 > 0 ? mono() - g_t0 : 0.0, body);
    if (g_side >= 0 && write(g_side, line, (size_t)n) < 0) { /* best effort */ }
    fputs(line, stdout);
    fflush(stdout);
}

static void on_signal(int sig) { (void)sig; g_stop = 1; }

static void release_lock(void)
{
    if (g_lock >= 0) {
        close(g_lock);
        unlink(LOCK_PATH);
        g_lock = -1;
    }
}

static const char *ioreturn_name(int32_t rc)
{
    switch (rc) {
    case kIOReturnTimeout: return "timeout";
    case kIOReturnExclusiveAccess: return "exclusive access";
    case kIOReturnNotResponding: return "not responding";
    case kIOReturnNoDevice: return "no device";
    case kIOReturnOffline: return "offline";
    case kIOReturnAborted: return "aborted";
    case kUSBHostReturnPipeStalled: return "pipe stalled";
    default: return "other";
    }
}

static id reg_prop(io_registry_entry_t e, NSString *key)
{
    return CFBridgingRelease(IORegistryEntryCreateCFProperty(e, (__bridge CFStringRef)key, kCFAllocatorDefault, 0));
}

static long reg_num(io_registry_entry_t e, NSString *key)
{
    id v = reg_prop(e, key);
    return [v isKindOfClass:[NSNumber class]] ? [v longValue] : -1;
}

// The USB product string of the device above an interface (registry read only).
static NSString *product_of(io_service_t iface)
{
    io_registry_entry_t parent = 0;
    NSString *product = nil;
    if (IORegistryEntryGetParentEntry(iface, kIOServicePlane, &parent) == KERN_SUCCESS) {
        id v = reg_prop(parent, @"USB Product Name");
        if (![v isKindOfClass:[NSString class]]) v = reg_prop(parent, @"kUSBProductString");
        if ([v isKindOfClass:[NSString class]]) product = v;
        IOObjectRelease(parent);
    }
    return product;
}

typedef struct {
    io_service_t svc;
    int port, stage;
    long location, speed;
    char path[512];
} cand_t;

// Step 3: the whole identity from the registry, before anything is opened.
static BOOL identity_ok(io_service_t svc, int *stage, int *port)
{
    if (reg_num(svc, @"idVendor") != kVendor || reg_num(svc, @"idProduct") != kProduct) return NO;
    long bcd = reg_num(svc, @"bcdDevice");
    *stage = -1;
    for (int i = 0; i < 2; i++)
        if (bcd == (long)kStageBcd[i]) *stage = i;
    if (*stage < 0) return NO;
    if (reg_num(svc, @"bInterfaceNumber") != kInterfaceNumber || reg_num(svc, @"bConfigurationValue") != kConfigValue ||
        reg_num(svc, @"bInterfaceClass") != kVendorClass || reg_num(svc, @"bInterfaceSubClass") != 0 ||
        reg_num(svc, @"bInterfaceProtocol") != 0)
        return NO;
    NSString *product = product_of(svc);
    if (![product hasPrefix:kProductPrefix] || [product length] != [kProductPrefix length] + 1) return NO;
    unichar c = [product characterAtIndex:[kProductPrefix length]];
    if (c < '1' || c > '9') return NO;
    *port = c - '0';
    return YES;
}

// Step 2: match the interface by the fixed identity. Returns the candidates (retained services).
static int find_candidates(int want_port, cand_t *out, int max, int *mismatches)
{
    int n = 0;
    *mismatches = 0;
    for (int s = 0; s < 2; s++) {
        CFMutableDictionaryRef match = [IOUSBHostInterface createMatchingDictionaryWithVendorID:@(kVendor)
                                                                                      productID:@(kProduct)
                                                                                      bcdDevice:@(kStageBcd[s])
                                                                                interfaceNumber:@(kInterfaceNumber)
                                                                             configurationValue:@(kConfigValue)
                                                                                 interfaceClass:@(kVendorClass)
                                                                              interfaceSubclass:@0
                                                                              interfaceProtocol:@0
                                                                                          speed:nil
                                                                                 productIDArray:nil];
        io_iterator_t it = 0;
        if (IOServiceGetMatchingServices(kIOMainPortDefault, match, &it) != KERN_SUCCESS) continue;  // consumes match
        io_service_t svc;
        while ((svc = IOIteratorNext(it))) {
            int stage = -1, port = 0;
            if (!identity_ok(svc, &stage, &port)) {
                (*mismatches)++;
                IOObjectRelease(svc);
            } else if ((want_port && port != want_port) || n >= max) {
                IOObjectRelease(svc);
            } else {
                cand_t *c = &out[n++];
                memset(c, 0, sizeof *c);
                c->svc = svc;
                c->port = port;
                c->stage = stage;
                c->location = reg_num(svc, @"locationID");
                c->speed = reg_num(svc, @"USBSpeed");
                io_string_t path;
                if (IORegistryEntryGetPath(svc, kIOServicePlane, path) == KERN_SUCCESS) snprintf(c->path, sizeof c->path, "%s", path);
            }
        }
        IOObjectRelease(it);
    }
    return n;
}

// Registry-only account of what macOS shows for 1d6b:0104 (the attempt-18 case: a device, no interface).
static void diagnose_absence(void)
{
    io_iterator_t it = 0;
    if (IORegistryCreateIterator(kIOMainPortDefault, "IOUSB", kIORegistryIterateRecursively, &it) != KERN_SUCCESS) {
        side("diagnostic: the USB plane cannot be iterated");
        return;
    }
    int found = 0;
    io_registry_entry_t e;
    while ((e = IOIteratorNext(it))) {
        if (reg_num(e, @"idVendor") == kVendor && reg_num(e, @"idProduct") == kProduct) {
            found++;
            id product = reg_prop(e, @"USB Product Name");
            side("diagnostic: 1d6b:0104 is present: bcdDevice 0x%04lx, speed %ld, product \"%s\"", reg_num(e, @"bcdDevice"),
                 reg_num(e, @"USBSpeed"), [product isKindOfClass:[NSString class]] ? [product UTF8String] : "?");
            io_iterator_t kids = 0;
            int n = 0;
            if (IORegistryEntryGetChildIterator(e, kIOServicePlane, &kids) == KERN_SUCCESS) {
                io_registry_entry_t k;
                while ((k = IOIteratorNext(kids))) {
                    io_name_t cls;
                    IOObjectGetClass(k, cls);
                    long number = reg_num(k, @"bInterfaceNumber");
                    if (number >= 0)
                        side("diagnostic:   child %s, interface %ld, class 0x%02lx", cls, number, reg_num(k, @"bInterfaceClass"));
                    else
                        side("diagnostic:   child %s", cls);
                    n++;
                    IOObjectRelease(k);
                }
                IOObjectRelease(kids);
            }
            if (!n) side("diagnostic:   no child at all in the service plane");
        }
        IOObjectRelease(e);
    }
    IOObjectRelease(it);
    if (!found) side("diagnostic: no 1d6b:0104 device in the USB plane");
}

// What owns an interface that refused the open (registry read only).
static void report_children(io_service_t svc)
{
    io_iterator_t kids = 0;
    if (IORegistryEntryGetChildIterator(svc, kIOServicePlane, &kids) != KERN_SUCCESS) return;
    int n = 0;
    io_registry_entry_t k;
    while ((k = IOIteratorNext(kids))) {
        io_name_t cls;
        IOObjectGetClass(k, cls);
        side("owner: child of the interface: %s", cls);
        n++;
        IOObjectRelease(k);
    }
    IOObjectRelease(kids);
    if (!n) side("owner: no child under the interface; another client holds it open");
}

static void sync_files(int capfd)
{
    if (capfd >= 0) fsync(capfd);
    if (g_side >= 0) fsync(g_side);
}

// Step 7: read the bulk-IN pipe one request at a time. After every return the reported byte
// count goes to the capture, even when the status is a timeout. Returns the exit code.
static int read_loop(id pipe, NSMutableData *buf, int capfd, double max_seconds, unsigned long long *total_out)
{
    unsigned long long total = 0;
    double start = mono(), last_report = start;
    int consecutive_other = 0;
    const char *reason = "";
    int code = 0;
    for (;;) {
        double now = mono();
        if (g_stop) { reason = "signal"; code = total ? 0 : 5; break; }
        if (g_terminated) { reason = "the interface service was terminated"; code = total ? 0 : 5; break; }
        if (now - start >= max_seconds) { reason = "--seconds reached"; code = total ? 0 : 5; break; }
        NSUInteger got = 0;
        NSError *err = nil;
        BOOL ok = [pipe sendIORequestWithData:buf bytesTransferred:&got completionTimeout:READ_TIMEOUT error:&err];
        if (got > (NSUInteger)[buf length]) got = [buf length];
        if (got > 0) {
            const unsigned char *p = [buf bytes];
            size_t off = 0;
            while (off < got) {
                ssize_t w = write(capfd, p + off, got - off);
                if (w < 0 && errno == EINTR) continue;
                if (w <= 0) {
                    side("write error on the capture (errno %d); stopping at once", errno);
                    *total_out = total;
                    return 6;
                }
                off += (size_t)w;
                total += (unsigned long long)w;
            }
        }
        if (!ok) {
            int32_t rc = (int32_t)[err code];
            side("status 0x%08x (%s) after %llu bytes", (uint32_t)rc, ioreturn_name(rc), total);
            if (rc == kIOReturnTimeout) {
                consecutive_other = 0;
            } else if (rc == kUSBHostReturnPipeStalled) {
                reason = "pipe stalled; the stall is not cleared by this tool";
                code = 5;
                break;
            } else if (rc == kIOReturnNotResponding || rc == kIOReturnNoDevice || rc == kIOReturnOffline || rc == kIOReturnAborted) {
                reason = "the device went away or is wedged";
                code = total ? 0 : 5;
                break;
            } else if (++consecutive_other >= 3) {
                reason = "three other errors in a row";
                code = 5;
                break;
            }
        } else {
            consecutive_other = 0;
        }
        if (total > MAX_CAPTURE) { reason = "capture above 64 MiB"; code = 5; break; }
        now = mono();
        if (now - last_report >= 1.0) {
            side("bytes %llu", total);
            sync_files(capfd);
            last_report = now;
        }
    }
    side("stopped: %s; %llu bytes captured", reason, total);
    sync_files(capfd);
    *total_out = total;
    return code;
}

static int usage(void)
{
    fputs("usage: bulk-log-reader --out FILE [--port N] [--wait 120] [--seconds 600] [--dry-run]\n", stderr);
    return 6;
}

static int refuse(const char *why)
{
    fprintf(stderr, "bulk-log-reader: refused: %s\n", why);
    return 6;
}

static void uptime_line(char *out, size_t n)
{
    struct timeval boot;
    size_t len = sizeof boot;
    int mib[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval now;
    gettimeofday(&now, NULL);
    if (sysctl(mib, 2, &boot, &len, NULL, 0) == 0)
        snprintf(out, n, "M1 uptime %ld s", (long)(now.tv_sec - boot.tv_sec));
    else
        snprintf(out, n, "M1 uptime unknown");
}

static int finish(int code, const char *reason)
{
    side("exit %d: %s", code, reason);
    if (g_side >= 0) { fsync(g_side); close(g_side); g_side = -1; }
    release_lock();
    return code;
}

int main(int argc, char **argv)
{
    @autoreleasepool {
        const char *out = NULL;
        int port = 0, wait_s = 120, seconds = 600, dry = 0;
        for (int i = 1; i < argc; i++) {
            if (!strcmp(argv[i], "--out") && i + 1 < argc) out = argv[++i];
            else if (!strcmp(argv[i], "--port") && i + 1 < argc) port = atoi(argv[++i]);
            else if (!strcmp(argv[i], "--wait") && i + 1 < argc) wait_s = atoi(argv[++i]);
            else if (!strcmp(argv[i], "--seconds") && i + 1 < argc) seconds = atoi(argv[++i]);
            else if (!strcmp(argv[i], "--dry-run")) dry = 1;
            else return usage();
        }
        if (!out || port < 0 || port > 9 || wait_s < 0 || seconds < 1) return usage();
        // Refusals come before any IOKit call.
        if (seconds > MAX_SECONDS_ALLOWED) return refuse("--seconds is above 3600");
        char sidecar[1100];
        snprintf(sidecar, sizeof sidecar, "%s.txt", out);
        struct stat st;
        if (!stat(out, &st)) return refuse("--out exists; a capture is never truncated or appended to");
        if (!stat(sidecar, &st)) return refuse("the sidecar file exists");
        g_lock = open(LOCK_PATH, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (g_lock < 0) return refuse(errno == EEXIST ? "another instance holds the lock file (remove a stale one by hand)"
                                                       : "the lock file cannot be created (build/native-intake must exist)");
        char pid[32];
        snprintf(pid, sizeof pid, "%d\n", (int)getpid());
        if (write(g_lock, pid, strlen(pid)) < 0) { /* informational */ }
        atexit(release_lock);
        g_side = open(sidecar, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (g_side < 0) { release_lock(); return refuse("the sidecar file cannot be created"); }

        struct sigaction sa;
        memset(&sa, 0, sizeof sa);
        sa.sa_handler = on_signal;
        sigaction(SIGINT, &sa, NULL);
        sigaction(SIGTERM, &sa, NULL);

        g_t0 = mono();
        char ts[40], up[64];
        utc(ts, sizeof ts);
        uptime_line(up, sizeof up);
        side("start %s; %s; mode %s; wait %d s; read limit %d s; port %s", ts, up, dry ? "dry-run (nothing is opened)" : "read",
             wait_s, seconds, port ? (char[]){ (char)('0' + port), 0 } : "any");

        cand_t cands[8];
        int n = 0, mismatches = 0;
        for (;;) {
            n = find_candidates(port, cands, 8, &mismatches);
            if (n > 0 || g_stop || mono() - g_t0 >= wait_s) break;
            usleep(500000);
        }
        if (n == 0) {
            if (g_stop) return finish(2, "interrupted while waiting; nothing matched");
            side("nothing matched within %d s (%d interface(s) of 1d6b:0104 failed the identity check)", wait_s, mismatches);
            diagnose_absence();
            return finish(2, "no matching interface: not set up by this tool; macOS never published one");
        }
        if (n > 1 && !port) {
            for (int i = 0; i < n; i++) {
                side("candidate: port %d, stage %s, locationID 0x%lx", cands[i].port, kStageName[cands[i].stage], cands[i].location);
                IOObjectRelease(cands[i].svc);
            }
            return finish(4, "several matches and no --port: pick one");
        }
        cand_t *c = &cands[0];
        side("identity: iLinux J716c control channel, port %d; stage %s (bcdDevice 0x%04x); interface 0, class 0xff, configuration 1",
             c->port, kStageName[c->stage], kStageBcd[c->stage]);
        side("registry path %s; locationID 0x%lx; speed %ld", c->path, c->location, c->speed);
        if (dry) {
            for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
            return finish(0, "dry-run: identity verified, nothing opened");
        }

        // Step 4: open the interface only, with no special options.
        dispatch_queue_t queue = dispatch_queue_create("bulk-log-reader", DISPATCH_QUEUE_SERIAL);
        NSError *err = nil;
        IOUSBHostInterface *iface = [[IOUSBHostInterface alloc] initWithIOService:c->svc
                                                                          options:IOUSBHostObjectInitOptionsNone
                                                                            queue:queue
                                                                            error:&err
                                                                  interestHandler:^(IOUSBHostObject *obj, uint32_t message, void *arg) {
            (void)obj; (void)arg;
            if (message == kIOMessageServiceIsTerminated) g_terminated = 1;
        }];
        if (!iface) {
            int32_t rc = (int32_t)[err code];
            side("the interface could not be opened: 0x%08x (%s)", (uint32_t)rc, ioreturn_name(rc));
            report_children(c->svc);
            for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
            return finish(3, "open failed; nothing is seized or retried");
        }
        // Step 5: the descriptors macOS cached for the interface.
        const IOUSBInterfaceDescriptor *ifd = iface.interfaceDescriptor;
        const IOUSBConfigurationDescriptor *cfg = iface.configurationDescriptor;
        int bulk_in = 0, bulk_other = 0, others = 0;
        unsigned in_addr = 0, other_addr = 0;
        if (ifd && cfg && ifd->bInterfaceNumber == 0 && ifd->bInterfaceClass == kVendorClass && ifd->bNumEndpoints == 2 &&
            cfg->bConfigurationValue == kConfigValue) {
            for (const IOUSBEndpointDescriptor *ep = IOUSBGetNextEndpointDescriptor(cfg, ifd, NULL); ep;
                 ep = IOUSBGetNextEndpointDescriptor(cfg, ifd, (const IOUSBDescriptorHeader *)ep)) {
                if (IOUSBGetEndpointType(ep) != kIOUSBEndpointTypeBulk) { others++; continue; }
                if (IOUSBGetEndpointDirection(ep) == kIOUSBEndpointDirectionIn) { bulk_in++; in_addr = ep->bEndpointAddress; }
                else { bulk_other++; other_addr = ep->bEndpointAddress; }
            }
        }
        if (!ifd || !cfg || bulk_in != 1 || bulk_other != 1 || others != 0 || !(in_addr & 0x80)) {
            side("descriptor mismatch: bulk IN %d, other bulk %d, non-bulk %d (an interrupt endpoint is never expected here)", bulk_in,
                 bulk_other, others);
            [iface destroy];
            for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
            return finish(4, "descriptors are not the expected device; closed");
        }
        side("descriptors: interface 0 class 0xff, alternate setting %u, %u interface(s) in the configuration; bulk IN 0x%02x, other bulk 0x%02x",
             ifd->bAlternateSetting, cfg->bNumInterfaces, in_addr, other_addr);
        // Step 6: copy the IN pipe only.
        IOUSBHostPipe *pipe = [iface copyPipeWithAddress:in_addr error:&err];
        NSMutableData *buf = pipe ? [iface ioDataWithCapacity:READ_CAPACITY error:&err] : nil;
        if (!pipe || !buf) {
            int32_t rc = (int32_t)[err code];
            side("the IN pipe or its buffer could not be set up: 0x%08x (%s)", (uint32_t)rc, ioreturn_name(rc));
            pipe = nil;
            [iface destroy];
            for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
            return finish(3, "pipe setup failed");
        }
        int capfd = open(out, O_WRONLY | O_CREAT | O_EXCL, 0600);
        if (capfd < 0) {
            side("the capture file cannot be created (errno %d)", errno);
            pipe = nil;
            [iface destroy];
            for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
            return finish(6, "capture file refused");
        }
        side("reading the bulk-IN pipe into the capture (16384-byte requests, 5 s timeout)");
        unsigned long long total = 0;
        int code = read_loop(pipe, buf, capfd, seconds, &total);
        // Step 9: release the pipe, then destroy the interface so that pending IO is aborted on the host side
        // (the SDK's pipe class has no destroy of its own).
        pipe = nil;
        [iface destroy];
        fsync(capfd);
        close(capfd);
        for (int i = 0; i < n; i++) IOObjectRelease(cands[i].svc);
        return finish(code, code == 0 ? "done" : "stopped early; see the lines above");
    }
}
