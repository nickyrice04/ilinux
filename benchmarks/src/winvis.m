// winvis.m - report whether a process has windows on screen (current Space,
// not minimised).  Benchmarks record it, because a window that is not on
// screen is never drawn or composited, so presentation would go unmeasured.
// Uses CGWindowListCopyWindowInfo by PID; reads no window titles or contents.
//   clang -O2 winvis.m -o winvis -framework CoreGraphics -framework Foundation
//   winvis PID   ->  {"pid":N,"on_screen_windows":K,"largest":"WxH@X,Y"}
#import <CoreGraphics/CoreGraphics.h>
#import <Foundation/Foundation.h>

int main(int argc, char **argv)
{
    @autoreleasepool {
        if (argc < 2) {
            fprintf(stderr, "usage: winvis PID\n");
            return 2;
        }
        const int pid = atoi(argv[1]);
        CFArrayRef list = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly |
                                                     kCGWindowListExcludeDesktopElements,
                                                     kCGNullWindowID);
        int count = 0;
        CGRect best = CGRectZero;
        for (NSDictionary *w in (__bridge NSArray *)list) {
            /* any level: a measurement run may float the VM window (layer 3) */
            if ([w[(id)kCGWindowOwnerPID] intValue] != pid || [w[(id)kCGWindowAlpha] doubleValue] <= 0)
                continue;
            CGRect r;
            if (!CGRectMakeWithDictionaryRepresentation((__bridge CFDictionaryRef)w[(id)kCGWindowBounds], &r) ||
                r.size.width < 100 || r.size.height < 100)
                continue;
            count++;
            if (r.size.width * r.size.height > best.size.width * best.size.height)
                best = r;
        }
        if (list)
            CFRelease(list);
        printf("{\"pid\":%d,\"on_screen_windows\":%d,\"largest\":\"%.0fx%.0f@%.0f,%.0f\"}\n", pid, count,
               best.size.width, best.size.height, best.origin.x, best.origin.y);
    }
    return 0;
}
