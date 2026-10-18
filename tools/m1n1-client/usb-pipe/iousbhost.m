/* iousbhost.m: usb-pipe's macOS backend, built from the macOS SDK only (IOUSBHost, IOKit,
 * Foundation; no third-party package, kext, system extension or entitlement).
 *
 * What it touches: the IOUSBHostInterface nub of interface 1 of the M5's gadget, matched by
 * the fixed identity in usb-pipe.h, opened with IOUSBHostObjectInitOptionsNone (never
 * DeviceCapture, which needs an entitlement and takes the device from macOS, never
 * DeviceSeize, which evicts the current owner), and its two bulk pipes. It reads the bulk-IN
 * pipe and writes the bulk-OUT pipe, nothing else: no control request (macOS's own
 * enumeration and SET_CONFIGURATION are macOS's), no alternate setting, no stall clearing
 * (a stalled pipe ends the session and is reported), no idle policy, reset or power change,
 * and never the IOUSBHostDevice or interface 0 (the bulk-log reader's). The static check in
 * tools/m1n1-client/test_usb_pipe.py fails if any of those names appear here. */
#import <Foundation/Foundation.h>
#import <IOKit/IOKitLib.h>
#import <IOKit/IOMessage.h>
#import <IOKit/usb/IOUSBHostFamilyDefinitions.h>
#import <IOUSBHost/IOUSBHost.h>

#include "relay.h"
#include "usb-pipe.h"

#include <stdatomic.h>
#include <string.h>
#include <unistd.h>

struct usb_ctx {
    IOUSBHostInterface *intf;
    IOUSBHostPipe *in, *out;
    NSMutableData *inbuf;      /* RELAY_CHUNK bytes of kernel-mapped memory, length fixed */
    int write_timeout_s;
    FILE *log;
    _Atomic int terminated;    /* the service went away (cable out, M5 reset) */
    _Atomic int aborted;       /* ssh closed: reads must not block again */
    char err[240];
};

static void say(FILE *log, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
static void say(FILE *log, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    fputs("usb-pipe: ", log);
    vfprintf(log, fmt, ap);
    fputc('\n', log);
    fflush(log);
    va_end(ap);
}

static const char *ioreturn_name(IOReturn r)
{
    switch (r) {
    case kIOReturnTimeout: return "timeout";
    case kIOReturnAborted: return "aborted";
    case kIOReturnNoDevice: return "no such device";
    case kIOReturnNotResponding: return "device not responding";
    case kIOReturnOffline: return "device offline";
    case kIOReturnExclusiveAccess: return "exclusive access: another process or a driver holds it";
    case kIOReturnNotPermitted: return "not permitted";
    case kIOReturnNotOpen: return "not open";
    case kUSBHostReturnPipeStalled: return "pipe stalled (not cleared: that would be a control request)";
    default: return "";
    }
}

static void describe(char *buf, size_t n, const char *what, NSError *e)
{
    IOReturn code = (IOReturn)e.code;
    snprintf(buf, n, "%s: 0x%08x %s", what, (unsigned)code, ioreturn_name(code));
}

/* ---- the pipe_ops backend ---------------------------------------------------------- */

static ssize_t usb_read(void *ctx, void *buf, size_t len, int timeout_ms)
{
    struct usb_ctx *c = ctx;
    if (len > RELAY_CHUNK) len = RELAY_CHUNK;
    if (len > c->inbuf.length) len = c->inbuf.length;   /* the kernel-mapped buffer's own length */
    for (;;) {
        if (atomic_load(&c->aborted)) return RELAY_READ_ABORTED;
        if (atomic_load(&c->terminated)) return RELAY_READ_EOF;
        NSUInteger got = 0;
        NSError *e = nil;
        BOOL ok = [c->in sendIORequestWithData:c->inbuf bytesTransferred:&got
                           completionTimeout:(timeout_ms > 0 ? timeout_ms / 1000.0 : 0) error:&e];
        if (got > len) got = len;
        if (got) memcpy(buf, c->inbuf.bytes, got);
        if (ok) {
            if (got == 0) continue;   /* a zero-length packet closed a transfer: nothing to pass on */
            return (ssize_t)got;
        }
        IOReturn code = (IOReturn)e.code;
        if (code == kIOReturnTimeout) return got ? (ssize_t)got : RELAY_READ_TIMEOUT;
        if (got) return (ssize_t)got;   /* deliver first; the next call reports the state */
        if (code == kIOReturnAborted) return atomic_load(&c->aborted) ? RELAY_READ_ABORTED : RELAY_READ_EOF;
        describe(c->err, sizeof c->err, "read", e);
        if (code == kIOReturnNoDevice || code == kIOReturnNotResponding || code == kIOReturnOffline) {
            say(c->log, "%s", c->err);
            return RELAY_READ_EOF;   /* the device went away */
        }
        return RELAY_READ_ERROR;
    }
}

static ssize_t usb_write(void *ctx, const void *buf, size_t len)
{
    struct usb_ctx *c = ctx;
    size_t done = 0;
    while (done < len) {
        if (atomic_load(&c->terminated)) {
            snprintf(c->err, sizeof c->err, "write: the device went away");
            return -1;
        }
        size_t n = len - done;
        if (n > RELAY_CHUNK) n = RELAY_CHUNK;
        NSMutableData *d = [NSMutableData dataWithBytes:(const char *)buf + done length:n];
        NSUInteger sent = 0;
        NSError *e = nil;
        if (![c->out sendIORequestWithData:d bytesTransferred:&sent completionTimeout:c->write_timeout_s error:&e]) {
            describe(c->err, sizeof c->err, "write", e);
            if ((IOReturn)e.code == kIOReturnTimeout)
                snprintf(c->err, sizeof c->err, "write: not accepted within %d s: nothing on the M5 reads "
                         "its SSH port (ilinux-sshd-tty@ttyGS<n> not running?)", c->write_timeout_s);
            return -1;
        }
        if (sent == 0) {
            snprintf(c->err, sizeof c->err, "write: the pipe accepted nothing");
            return -1;
        }
        done += sent;
    }
    return (ssize_t)len;
}

static void usb_abort(void *ctx)
{
    struct usb_ctx *c = ctx;
    atomic_store(&c->aborted, 1);
    NSError *e = nil;
    [c->in abortWithOption:IOUSBHostAbortOptionSynchronous error:&e];
}

static const char *usb_error(void *ctx)
{
    return ((struct usb_ctx *)ctx)->err;
}

/* ---- finding and checking the interface ---------------------------------------------- */

struct candidate {
    io_service_t service;
    int port;
    unsigned location;
    char path[512];
    char product[160];
};

static long long prop_number(io_service_t s, CFStringRef key)
{
    CFTypeRef v = IORegistryEntryCreateCFProperty(s, key, kCFAllocatorDefault, 0);
    long long out = -1;
    if (v && CFGetTypeID(v) == CFNumberGetTypeID()) CFNumberGetValue(v, kCFNumberLongLongType, &out);
    if (v) CFRelease(v);
    return out;
}

static NSString *parent_string(io_service_t s, CFStringRef key)
{
    CFTypeRef v = IORegistryEntrySearchCFProperty(s, kIOServicePlane, key, kCFAllocatorDefault,
                                                  kIORegistryIterateRecursively | kIORegistryIterateParents);
    if (v && CFGetTypeID(v) == CFStringGetTypeID()) return CFBridgingRelease(v);
    if (v) CFRelease(v);
    return nil;
}

static long long parent_number(io_service_t s, CFStringRef key)
{
    CFTypeRef v = IORegistryEntrySearchCFProperty(s, kIOServicePlane, key, kCFAllocatorDefault,
                                                  kIORegistryIterateRecursively | kIORegistryIterateParents);
    long long out = -1;
    if (v && CFGetTypeID(v) == CFNumberGetTypeID()) CFNumberGetValue(v, kCFNumberLongLongType, &out);
    if (v) CFRelease(v);
    return out;
}

/* The registry's view of one matched interface, checked field by field against the fixed
 * identity before anything is opened. Returns 0 and fills c, or -1 with the reason in why. */
static int check_candidate(io_service_t s, struct candidate *c, char *why, size_t n)
{
    struct { const char *name; CFStringRef key; long long want; int optional; } fields[] = {
        { "idVendor", CFSTR(kUSBHostMatchingPropertyVendorID), USB_PIPE_VENDOR_ID, 0 },
        { "idProduct", CFSTR(kUSBHostMatchingPropertyProductID), USB_PIPE_PRODUCT_ID, 0 },
        { "bcdDevice", CFSTR(kUSBHostMatchingPropertyDeviceReleaseNumber), USB_PIPE_BCD_DEVICE, 0 },
        { "bConfigurationValue", CFSTR(kUSBHostMatchingPropertyConfigurationValue), USB_PIPE_CONFIGURATION, 0 },
        { "bInterfaceNumber", CFSTR(kUSBHostMatchingPropertyInterfaceNumber), USB_PIPE_INTERFACE, 0 },
        { "bInterfaceClass", CFSTR(kUSBHostMatchingPropertyInterfaceClass), USB_PIPE_INTERFACE_CLASS, 0 },
        { "bInterfaceSubClass", CFSTR(kUSBHostMatchingPropertyInterfaceSubClass), 0, 0 },
        { "bInterfaceProtocol", CFSTR(kUSBHostMatchingPropertyInterfaceProtocol), 0, 0 },
        { "bAlternateSetting", CFSTR(kUSBHostInterfacePropertyAlternateSetting), 0, 1 },
    };
    memset(c, 0, sizeof *c);
    c->service = s;
    for (size_t i = 0; i < sizeof fields / sizeof *fields; i++) {
        long long v = prop_number(s, fields[i].key);
        if (v == -1 && fields[i].optional) continue;   /* not published on every nub; the descriptor check covers it */
        if (v != fields[i].want) {
            snprintf(why, n, "%s is 0x%llx, not 0x%llx", fields[i].name, v, fields[i].want);
            return -1;
        }
    }
    NSString *product = parent_string(s, CFSTR(kUSBHostDevicePropertyProductString));
    const char *p = product ? product.UTF8String : "";
    size_t plen = strlen(USB_PIPE_PRODUCT_PREFIX);
    if (strncmp(p, USB_PIPE_PRODUCT_PREFIX, plen) || p[plen] < '1' || p[plen] > '3' || p[plen + 1]) {
        snprintf(why, n, "product string is not \"%sN\"", USB_PIPE_PRODUCT_PREFIX);
        return -1;
    }
    snprintf(c->product, sizeof c->product, "%s", p);
    c->port = p[plen] - '0';
    long long loc = parent_number(s, CFSTR(kUSBHostPropertyLocationID));
    c->location = loc < 0 ? 0 : (unsigned)loc;
    io_string_t path;
    if (IORegistryEntryGetPath(s, kIOServicePlane, path) == KERN_SUCCESS) snprintf(c->path, sizeof c->path, "%s", path);
    return 0;
}

/* Poll the registry for up to wait_s seconds. Fills found (at most max) and returns the count. */
static int find_candidates(const struct usb_pipe_options *o, FILE *log, struct candidate *found, int max)
{
    int count = 0, rejected_reported = 0;
    for (int tick = 0;; tick++) {
        CFMutableDictionaryRef dict = [IOUSBHostInterface createMatchingDictionaryWithVendorID:@USB_PIPE_VENDOR_ID
            productID:@USB_PIPE_PRODUCT_ID bcdDevice:@USB_PIPE_BCD_DEVICE interfaceNumber:@USB_PIPE_INTERFACE
            configurationValue:@USB_PIPE_CONFIGURATION interfaceClass:@USB_PIPE_INTERFACE_CLASS
            interfaceSubclass:@0 interfaceProtocol:@0 speed:nil productIDArray:nil];
        io_iterator_t it = IO_OBJECT_NULL;
        count = 0;
        if (IOServiceGetMatchingServices(kIOMainPortDefault, dict, &it) == KERN_SUCCESS) {   /* consumes dict */
            io_service_t s;
            while ((s = IOIteratorNext(it))) {
                struct candidate c;
                char why[200];
                if (check_candidate(s, &c, why, sizeof why) == 0) {
                    if ((o->port == 0 || o->port == c.port) && count < max) found[count++] = c;
                    else IOObjectRelease(s);
                } else {
                    if (!rejected_reported++) say(log, "a 1d6b:0104 interface matched but is not the M5's SSH pipe: %s", why);
                    IOObjectRelease(s);
                }
            }
            IOObjectRelease(it);
        }
        if (count || tick * 500 >= o->wait_s * 1000) return count;
        usleep(500000);
    }
}

static void release_candidates(struct candidate *c, int n)
{
    for (int i = 0; i < n; i++) IOObjectRelease(c[i].service);
}

/* ---- main ---------------------------------------------------------------------------- */

int usb_pipe_backend_main(const struct usb_pipe_options *o, FILE *log)
{
    @autoreleasepool {
        say(log, "version %s: waiting up to %d s for 1d6b:0104 bcdDevice 0x%04x, configuration %d, "
            "interface %d (class 0x%02x, the SSH byte pipe)%s", USB_PIPE_VERSION, o->wait_s, USB_PIPE_BCD_DEVICE,
            USB_PIPE_CONFIGURATION, USB_PIPE_INTERFACE, USB_PIPE_INTERFACE_CLASS, o->port ? ", one port" : "");
        struct candidate found[8];
        int n = find_candidates(o, log, found, 8);
        if (n == 0) {
            say(log, "no matching interface in %d s%s", o->wait_s,
                o->port ? " (for the requested port)" : "");
            return USB_PIPE_EXIT_NO_DEVICE;
        }
        for (int i = 0; i < n; i++)
            say(log, "%s: port %d, locationID 0x%08x, %s", n > 1 ? "candidate" : "found", found[i].port,
                found[i].location, found[i].path);
        if (n > 1) {
            say(log, "%d interfaces match: say which with --port N", n);
            release_candidates(found, n);
            return USB_PIPE_EXIT_IDENTITY;
        }
        if (o->dry_run) {
            say(log, "dry run: \"%s\" verified; not opened", found[0].product);
            release_candidates(found, n);
            return USB_PIPE_EXIT_OK;
        }

        struct usb_ctx *c = calloc(1, sizeof *c);
        __block struct usb_ctx *ctx = c;
        c->log = log;
        c->write_timeout_s = o->write_timeout_s;
        NSError *e = nil;
        IOUSBHostInterface *intf = [[IOUSBHostInterface alloc] initWithIOService:found[0].service
            options:IOUSBHostObjectInitOptionsNone queue:nil error:&e
            interestHandler:^(IOUSBHostObject *object, uint32_t messageType, void *messageArgument) {
                (void)object; (void)messageArgument;
                if (messageType == kIOMessageServiceIsTerminated) {
                    atomic_store(&ctx->terminated, 1);
                    say(ctx->log, "the interface was terminated (cable out or M5 reset)");
                    NSError *ae = nil;
                    [ctx->in abortWithOption:IOUSBHostAbortOptionAsynchronous error:&ae];
                    [ctx->out abortWithOption:IOUSBHostAbortOptionAsynchronous error:&ae];
                }
            }];
        /* The object keeps the io_service_t reference it was given and releases it itself
         * (IOUSBHostObject.h); only the candidates not opened are ours to release. */
        release_candidates(found + 1, n - 1);
        if (!intf) {
            char why[240];
            describe(why, sizeof why, "open", e);
            say(log, "cannot open the interface (%s); not seizing it", why);
            IOObjectRelease(found[0].service);
            free(c);
            return USB_PIPE_EXIT_OPEN;
        }
        c->intf = intf;

        /* The descriptors macOS cached at enumeration: exactly what the gadget declares. */
        const IOUSBConfigurationDescriptor *cd = intf.configurationDescriptor;
        const IOUSBInterfaceDescriptor *id = intf.interfaceDescriptor;
        int in_addr = -1, out_addr = -1, bad = 0, in_mps = 0;
        if (!cd || !id || cd->bNumInterfaces != USB_PIPE_INTERFACES_IN_CONFIGURATION ||
            id->bInterfaceNumber != USB_PIPE_INTERFACE || id->bInterfaceClass != USB_PIPE_INTERFACE_CLASS ||
            id->bNumEndpoints != 2) {
            bad = 1;
        } else {
            const IOUSBEndpointDescriptor *ep = NULL;
            while ((ep = IOUSBGetNextEndpointDescriptor(cd, id, (const IOUSBDescriptorHeader *)ep))) {
                uint8_t type = IOUSBGetEndpointType(ep), dir = IOUSBGetEndpointDirection(ep);
                if (type != kIOUSBEndpointTypeBulk) bad = 1;
                else if (dir == kIOUSBEndpointDirectionIn && in_addr < 0) {
                    in_addr = IOUSBGetEndpointAddress(ep);
                    in_mps = ep->wMaxPacketSize & 0x7ff;
                } else if (dir == kIOUSBEndpointDirectionOut && out_addr < 0) out_addr = IOUSBGetEndpointAddress(ep);
                else bad = 1;
            }
        }
        if (bad || in_addr < 0 || out_addr < 0) {
            say(log, "descriptors are not the SSH byte pipe's (%d interfaces, interface %d class 0x%02x with %d "
                "endpoints): closing", cd ? cd->bNumInterfaces : -1, id ? id->bInterfaceNumber : -1,
                id ? id->bInterfaceClass : 0, id ? id->bNumEndpoints : -1);
            [intf destroy];
            free(c);
            return USB_PIPE_EXIT_IDENTITY;
        }
        say(log, "interface open: bulk IN 0x%02x (%d-byte packets), bulk OUT 0x%02x, %d interfaces in the "
            "configuration", in_addr, in_mps, out_addr, cd->bNumInterfaces);
        c->in = [intf copyPipeWithAddress:(NSUInteger)in_addr error:&e];
        if (c->in) c->out = [intf copyPipeWithAddress:(NSUInteger)out_addr error:&e];
        if (c->in) c->inbuf = [intf ioDataWithCapacity:RELAY_CHUNK error:&e];
        if (c->inbuf && c->inbuf.length == 0) {   /* a buffer that cannot take a transfer is no buffer */
            say(log, "the IO buffer has length 0 (capacity %d requested)", RELAY_CHUNK);
            c->inbuf = nil;
        }
        if (!c->in || !c->out || !c->inbuf) {
            char why[240];
            describe(why, sizeof why, "pipes", e);
            say(log, "cannot open the pipes (%s)", why);
            c->inbuf = nil;
            c->in = nil;
            c->out = nil;
            [intf destroy];   /* closes the user client; the pipes go with it */
            free(c);
            return USB_PIPE_EXIT_OPEN;
        }

        struct pipe_ops ops = { c, usb_read, usb_write, usb_abort, usb_error };
        struct relay_options ro = { o->banner_wait_ms, o->quiet_ms, log };
        struct relay_stats st;
        int rc = relay_run(&ops, STDIN_FILENO, STDOUT_FILENO, &ro, &st);
        /* Abort what is still pending on the host side and close the user client; nothing is
         * sent to the M5. IOUSBHostPipe has no destroy of its own: the interface's covers it. */
        NSError *ae = nil;
        [c->in abortWithOption:IOUSBHostAbortOptionSynchronous error:&ae];
        [c->out abortWithOption:IOUSBHostAbortOptionSynchronous error:&ae];
        c->inbuf = nil;   /* the kernel-backed buffer goes before its user client */
        c->in = nil;
        c->out = nil;
        [intf destroy];
        c->intf = nil;
        if (atomic_load(&c->terminated) && rc == 0) say(log, "ended because the device went away");
        free(c);
        return rc;
    }
}
