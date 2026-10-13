#!/bin/sh
set -eu
[ "$(uname -s)" = Linux ] || { echo 'Run only inside isolated Linux'; exit 2; }
cd "$(dirname "$0")"
cc --version > compiler.txt
uname -srvmo > environment.txt
for variant in baseline patched; do
    cc -O2 -std=c11 -Wall -Wextra -Werror -I"$variant" test_startup.c -o "$variant/test-startup"
done
if ./baseline/test-startup mismatch > baseline-mismatch.txt 2>&1; then
    echo 'Baseline did not reproduce'; exit 1
fi
# Require the controlled assertion, rather than accepting a crash as reproduction.
grep -qx 'FAIL mismatch: reads=2 writes32=2 writes64=0 waits=0' baseline-mismatch.txt
for case in mismatch match unlocked already-started out-of-range el3-out-of-range el3-match timeout; do
    ./patched/test-startup "$case"
    if [ "$case" != mismatch ]; then ./baseline/test-startup "$case"; fi
done
if command -v clang >/dev/null; then
    clang -O1 -g -std=c11 -Wall -Wextra -Werror -fsanitize=address,undefined \
        -fno-omit-frame-pointer -Ipatched test_startup.c -o patched/test-startup-sanitized
    for case in mismatch match unlocked already-started out-of-range el3-out-of-range el3-match timeout; do
        ./patched/test-startup-sanitized "$case"
    done
    clang --version > sanitizer-compiler.txt
else
    echo 'Sanitizers unavailable' > sanitizer-compiler.txt
fi
cd object
cc -O2 -Wall -g -Wundef -Werror=strict-prototypes -fno-common -fno-PIE \
    -Werror=implicit-function-declaration -Werror=implicit-int \
    -Wsign-compare -Wunused-parameter -Wno-multichar \
    -ffreestanding -fpic -ffunction-sections -fdata-sections \
    -nostdinc -isystem "$(cc -print-file-name=include)" -isystem sysinc \
    -Isrc -Isrc/hv -fno-stack-protector -mstrict-align -march=armv8.2-a \
    -mgeneral-regs-only -c src/smp.c -o smp.o
readelf -h smp.o
