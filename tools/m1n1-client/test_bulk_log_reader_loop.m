// test_bulk_log_reader_loop.m: runs read_loop() of bulk-log-reader.m against a fake pipe.
// No USB, no device access: the fake answers the same read selector with scripted byte counts and
// IOReturn codes, so the loop's handling of data, timeouts, stalls, errors and limits is checked on
// the code that ships. Build and run from test_bulk_log_reader.py (or by hand):
//   clang -fobjc-arc -framework Foundation -framework IOKit -framework IOUSBHost \
//     -o /tmp/loop-test tools/m1n1-client/test_bulk_log_reader_loop.m && /tmp/loop-test

#define main reader_main
#include "bulk-log-reader.m"
#undef main

typedef struct { unsigned bytes; int32_t rc; double delay; int set_terminated; int set_stop; } step_t;

static unsigned long long g_produced;   // running byte counter: the capture must read 0,1,2,... mod 256

@interface FakePipe : NSObject {
@public
    const step_t *steps;
    int count, index;
}
- (BOOL)sendIORequestWithData:(NSMutableData *)data
             bytesTransferred:(NSUInteger *)bytesTransferred
            completionTimeout:(NSTimeInterval)timeout
                        error:(NSError **)error;
@end

@implementation FakePipe
- (BOOL)sendIORequestWithData:(NSMutableData *)data
             bytesTransferred:(NSUInteger *)bytesTransferred
            completionTimeout:(NSTimeInterval)timeout
                        error:(NSError **)error
{
    (void)timeout;
    step_t s = steps[index < count ? index : count - 1];   // the last step repeats
    index++;
    if (s.delay > 0) usleep((useconds_t)(s.delay * 1e6));
    unsigned char *p = [data mutableBytes];
    for (unsigned i = 0; i < s.bytes; i++) p[i] = (unsigned char)(g_produced++ & 0xff);
    *bytesTransferred = s.bytes;
    if (s.set_terminated) g_terminated = 1;
    if (s.set_stop) g_stop = 1;
    if (s.rc) {
        *error = [NSError errorWithDomain:IOUSBHostErrorDomain code:s.rc userInfo:nil];
        return NO;
    }
    return YES;
}
@end

static int failures;

#define CHECK(cond, ...) do { if (!(cond)) { printf("  FAIL: " __VA_ARGS__); printf("\n"); failures++; } } while (0)

// Runs one scenario; returns the loop's exit code. The capture goes to a temp file (or an invalid fd).
static int run(const char *name, const step_t *steps, int count, double max_seconds, unsigned long long expect_bytes,
               int bad_fd, unsigned long long *size_out, int *calls_out)
{
    printf("scenario: %s\n", name);
    g_stop = 0;
    g_terminated = 0;
    g_produced = 0;
    char path[] = "/tmp/bulk-log-loop-XXXXXX";
    int fd = bad_fd ? -1 : mkstemp(path);
    FakePipe *pipe = [FakePipe new];
    pipe->steps = steps;
    pipe->count = count;
    NSMutableData *buf = [NSMutableData dataWithLength:READ_CAPACITY];
    unsigned long long total = 0;
    int code = read_loop(pipe, buf, fd, max_seconds, &total);
    *calls_out = pipe->index;
    if (!bad_fd) {
        struct stat st;
        fstat(fd, &st);
        *size_out = (unsigned long long)st.st_size;
        if (expect_bytes != (unsigned long long)-1) CHECK((unsigned long long)st.st_size == expect_bytes, "capture is %lld bytes, expected %llu", (long long)st.st_size, expect_bytes);
        CHECK(*size_out == total, "file size %llu differs from the loop's own count %llu", *size_out, total);
        // order check: byte i of the file must be i mod 256
        FILE *f = fopen(path, "rb");
        unsigned long long i = 0;
        int c;
        while ((c = fgetc(f)) != EOF && i < 200000) { if (c != (int)(i & 0xff)) { CHECK(0, "capture byte %llu is %d", i, c); break; } i++; }
        fclose(f);
        close(fd);
        unlink(path);
    }
    return code;
}

int main(void)
{
    @autoreleasepool {
        g_side = open("/dev/null", O_WRONLY);
        g_t0 = mono();
        unsigned long long size = 0;
        int calls = 0, code;
        const int32_t TIMEOUT = (int32_t)kIOReturnTimeout, GONE = (int32_t)kIOReturnNoDevice, NORESP = (int32_t)kIOReturnNotResponding;
        const int32_t STALL = (int32_t)kUSBHostReturnPipeStalled, OTHER = (int32_t)kIOReturnError;

        { // data, quiet timeouts, a timeout that still carried bytes, data, then the device goes away
            const step_t s[] = { {1000, 0, 0, 0, 0}, {0, TIMEOUT, 0, 0, 0}, {0, TIMEOUT, 0, 0, 0}, {300, TIMEOUT, 0, 0, 0}, {16384, 0, 0, 0, 0}, {0, 0, 0, 0, 0}, {0, GONE, 0, 0, 0} };
            code = run("data, timeouts, bytes on a timeout, then the device goes away", s, 7, 30, 1000 + 300 + 16384, 0, &size, &calls);
            CHECK(code == 0, "exit %d, expected 0 (data arrived)", code);
            CHECK(calls == 7, "%d reads, expected 7", calls);
        }
        { // a stall is not cleared: stop at once, keep the bytes
            const step_t s[] = { {500, 0, 0, 0, 0}, {0, STALL, 0, 0, 0}, {777, 0, 0, 0, 0} };
            code = run("stall after data", s, 3, 30, 500, 0, &size, &calls);
            CHECK(code == 5, "exit %d, expected 5", code);
            CHECK(calls == 2, "%d reads, expected 2 (no read after the stall)", calls);
        }
        { // the device is not responding and nothing ever arrived
            const step_t s[] = { {0, TIMEOUT, 0, 0, 0}, {0, NORESP, 0, 0, 0}, {10, 0, 0, 0, 0} };
            code = run("not responding, no data", s, 3, 30, 0, 0, &size, &calls);
            CHECK(code == 5, "exit %d, expected 5", code);
            CHECK(calls == 2, "%d reads, expected 2", calls);
        }
        { // three other errors in a row stop the loop
            const step_t s[] = { {100, 0, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {50, 0, 0, 0, 0} };
            code = run("three other errors in a row", s, 5, 30, 100, 0, &size, &calls);
            CHECK(code == 5, "exit %d, expected 5", code);
            CHECK(calls == 4, "%d reads, expected 4", calls);
        }
        { // two other errors, a success resets the count, then the device goes away
            const step_t s[] = { {0, OTHER, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {64, 0, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {0, OTHER, 0, 0, 0}, {0, GONE, 0, 0, 0} };
            code = run("two errors, a success, two errors, then gone", s, 6, 30, 64, 0, &size, &calls);
            CHECK(code == 0, "exit %d, expected 0", code);
            CHECK(calls == 6, "%d reads, expected 6", calls);
        }
        { // the capture cap: more than 64 MiB stops the loop
            const step_t s[] = { {16384, 0, 0, 0, 0} };
            code = run("capture above 64 MiB", s, 1, 600, (unsigned long long)-1, 0, &size, &calls);
            CHECK(code == 5, "exit %d, expected 5", code);
            CHECK(size > MAX_CAPTURE && size <= MAX_CAPTURE + READ_CAPACITY, "stopped at %llu bytes", size);
        }
        { // a write error on the capture stops reading at once with exit 6
            const step_t s[] = { {4096, 0, 0, 0, 0}, {4096, 0, 0, 0, 0} };
            code = run("write error on the capture", s, 2, 30, 0, 1, &size, &calls);
            CHECK(code == 6, "exit %d, expected 6", code);
            CHECK(calls == 1, "%d reads, expected 1", calls);
        }
        { // the interface service is terminated while data flows
            const step_t s[] = { {2048, 0, 0, 0, 0}, {2048, 0, 0, 1, 0}, {2048, 0, 0, 0, 0} };
            code = run("service terminated after data", s, 3, 30, 4096, 0, &size, &calls);
            CHECK(code == 0, "exit %d, expected 0", code);
            CHECK(calls == 2, "%d reads, expected 2", calls);
        }
        { // SIGINT or SIGTERM while data flows
            const step_t s[] = { {1024, 0, 0, 0, 0}, {1024, 0, 0, 0, 1}, {1024, 0, 0, 0, 0} };
            code = run("signal after data", s, 3, 30, 2048, 0, &size, &calls);
            CHECK(code == 0, "exit %d, expected 0", code);
            CHECK(calls == 2, "%d reads, expected 2", calls);
        }
        { // the --seconds limit with data earlier
            const step_t s[] = { {512, 0, 0, 0, 0}, {0, TIMEOUT, 0.06, 0, 0} };
            code = run("--seconds limit reached after data", s, 2, 0.4, 512, 0, &size, &calls);
            CHECK(code == 0, "exit %d, expected 0", code);
            CHECK(calls >= 3 && calls < 20, "%d reads", calls);
        }
        { // the --seconds limit with no data at all
            const step_t s[] = { {0, TIMEOUT, 0.06, 0, 0} };
            code = run("--seconds limit reached with no data", s, 1, 0.3, 0, 0, &size, &calls);
            CHECK(code == 5, "exit %d, expected 5", code);
        }
        printf(failures ? "FAILED: %d check(s)\n" : "PASS: all read-loop scenarios\n", failures);
        return failures ? 1 : 0;
    }
}
