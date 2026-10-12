// occlude.m - cover the QEMU VM window with an opaque window for a while, so
// macOS treats the VM as hidden (App Nap eligible) without touching any other
// app.  Used to test the VM's App Nap policy deterministically.
//   clang -fobjc-arc -O2 occlude.m -o occlude -framework AppKit
//   occlude SECONDS [OWNER]   (OWNER defaults to qemu-system-aarch64)
// Window bounds come from CGWindowListCopyWindowInfo, which needs no screen
// recording permission for bounds and owner names.
#import <AppKit/AppKit.h>

int main(int argc, char **argv)
{
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "usage: occlude SECONDS [OWNER]\n");
            return 2;
        }
        const double secs = atof(argv[1]);
        NSString *owner = argc > 2 ? @(argv[2]) : @"qemu-system-aarch64";
        CFArrayRef list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly |
                                                     kCGWindowListExcludeDesktopElements,
                                                     kCGNullWindowID);
        CGRect best = CGRectNull;
        for (NSDictionary *w in (__bridge NSArray *)list) {
            if (![w[(id)kCGWindowOwnerName] isEqual:owner] || [w[(id)kCGWindowLayer] intValue] != 0)
                continue;
            CGRect r;
            if (!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds], &r))
                continue;
            if (CGRectIsNull(best) || r.size.width * r.size.height > best.size.width * best.size.height)
                best = r;
        }
        if (list)
            CFRelease(list);
        if (CGRectIsNull(best)) {
            fprintf(stderr, "occlude: no on-screen window owned by %s\n", owner.UTF8String);
            return 1;
        }
        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
        /* CG bounds are top-left based on the main display; AppKit is bottom-left */
        const CGFloat main_h = NSScreen.screens.firstObject.frame.size.height;
        const NSRect frame = NSMakeRect(best.origin.x - 2, main_h - best.origin.y - best.size.height - 2,
                                        best.size.width + 4, best.size.height + 4);
        NSWindow *win = [[NSWindow alloc] initWithContentRect:frame
                                                    styleMask:NSWindowStyleMaskBorderless
                                                      backing:NSBackingStoreBuffered
                                                        defer:NO];
        win.backgroundColor = NSColor.blackColor;
        win.opaque = YES;
        win.level = NSFloatingWindowLevel;
        [win orderFrontRegardless];
        printf("{\"bench\":\"occlude\",\"x\":%.0f,\"y\":%.0f,\"w\":%.0f,\"h\":%.0f,\"seconds\":%.1f}\n",
               best.origin.x, best.origin.y, best.size.width, best.size.height, secs);
        fflush(stdout);
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(secs * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{
            [NSApp terminate:nil];
        });
        [NSApp run];
    }
    return 0;
}
