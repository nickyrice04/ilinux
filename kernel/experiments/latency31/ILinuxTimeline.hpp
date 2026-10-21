#pragma once
// Original, opt-in CPU-side timeline; no GL fence or hardware operation.
// Single main thread only, bounded RAM-file output. IDs carry no user text.
#include <cstdint>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <time.h>
#include <unistd.h>
#include <sys/stat.h>
#include <pthread.h>

namespace ILinuxTimeline {
inline uint64_t ns(clockid_t id) {
    timespec t{};
    if (clock_gettime(id, &t)) return 0;
    return uint64_t(t.tv_sec) * 1000000000ULL + t.tv_nsec;
}
struct Writer {
    FILE* file = nullptr;
    uint64_t count = 0, sequence = 0;
    pthread_t owner = pthread_self();
    Writer() {
        const char* e = std::getenv("ILINUX_LATENCY_TRACE");
        if (!e || std::strcmp(e, "1") || getuid() != 1000) return;
        // Exclusive, no symlink; a second run must use a new disposable session.
        int fd = open("/run/user/1000/ilinux-timeline31.log", O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
        if (fd < 0) return;
        file = fdopen(fd, "w");
        if (!file) { close(fd); return; }
        setvbuf(file, nullptr, _IOLBF, 0);
        fputs("id,tag,start_ns,end_ns,cpu_ns,arg0,arg1\n", file);
    }
    ~Writer() { if (file) fclose(file); }
};
inline Writer& getWriter() { static Writer instance; return instance; }
struct Scope {
    const char* tag;
    uint64_t id = 0, start = 0, cpu = 0;
    int64_t a, b;
    Scope(const char* name, int64_t arg0 = 0, int64_t arg1 = 0) : tag(name), a(arg0), b(arg1) {
        auto& writer = getWriter();
        if (!pthread_equal(pthread_self(), writer.owner)) return;
        if (!writer.file || writer.count >= 100000) return;
        id = ++writer.sequence;
        start = ns(CLOCK_MONOTONIC);
        cpu = ns(CLOCK_THREAD_CPUTIME_ID);
    }
    ~Scope() {
        auto& writer = getWriter();
        if (!start || !writer.file || writer.count >= 100000) return;
        const auto end = ns(CLOCK_MONOTONIC), used = ns(CLOCK_THREAD_CPUTIME_ID) - cpu;
        ++writer.count;
        if (fprintf(writer.file, "%llu,%s,%llu,%llu,%llu,%lld,%lld\n",
                    (unsigned long long)id, tag, (unsigned long long)start, (unsigned long long)end,
                    (unsigned long long)used, (long long)a, (long long)b) < 0) {
            fclose(writer.file); writer.file = nullptr;
        }
    }
    Scope(const Scope&) = delete;
    Scope& operator=(const Scope&) = delete;
};
}
