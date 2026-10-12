// avplay.m - macOS-native playback reference for the VM video benchmarks.
// Loops a file in an AVPlayerLayer window (AVFoundation picks the hardware
// decoder) for a fixed time, without taking focus or a Dock icon, then prints
// one JSON line with AVFoundation's dropped-frame count.
//   clang -fobjc-arc -O2 avplay.m -o avplay -framework AppKit -framework AVFoundation
//   avplay FILE SECONDS [WIDTH_PT HEIGHT_PT]   (default 1296x729 pt, the VM window)
#import <AppKit/AppKit.h>
#import <AVFoundation/AVFoundation.h>

int main(int argc, char **argv)
{
    @autoreleasepool {
        if (argc < 3) {
            fprintf(stderr, "usage: avplay FILE SECONDS [WIDTH_PT HEIGHT_PT]\n");
            return 2;
        }
        NSURL *url = [NSURL fileURLWithPath:@(argv[1])];
        const double secs = atof(argv[2]);
        const CGFloat w = argc > 4 ? atof(argv[3]) : 1296, h = argc > 4 ? atof(argv[4]) : 729;

        [NSApplication sharedApplication];
        [NSApp setActivationPolicy:NSApplicationActivationPolicyAccessory];
        NSWindow *win = [[NSWindow alloc] initWithContentRect:NSMakeRect(0, 0, w, h)
                                                    styleMask:NSWindowStyleMaskBorderless
                                                      backing:NSBackingStoreBuffered
                                                        defer:NO];
        win.contentView.wantsLayer = YES;
        AVQueuePlayer *player = [AVQueuePlayer new];
        AVPlayerLooper *looper =
            [AVPlayerLooper playerLooperWithPlayer:player
                                      templateItem:[AVPlayerItem playerItemWithURL:url]];
        AVPlayerLayer *layer = [AVPlayerLayer playerLayerWithPlayer:player];
        layer.frame = win.contentView.bounds;
        [win.contentView.layer addSublayer:layer];
        [win center];
        [win orderFrontRegardless];
        [player play];
        dispatch_after(dispatch_time(DISPATCH_TIME_NOW, (int64_t)(secs * NSEC_PER_SEC)),
                       dispatch_get_main_queue(), ^{
            long dropped = 0;
            for (AVPlayerItem *item in looper.loopingPlayerItems)
                for (AVPlayerItemAccessLogEvent *ev in item.accessLog.events)
                    if (ev.numberOfDroppedVideoFrames > 0)
                        dropped += ev.numberOfDroppedVideoFrames;
            printf("{\"bench\":\"avplay\",\"seconds\":%.1f,\"dropped_frames\":%ld,\"loops\":%ld}\n",
                   secs, dropped, (long)looper.loopCount);
            fflush(stdout);
            [NSApp terminate:nil];
        });
        [NSApp run];
    }
    return 0;
}
