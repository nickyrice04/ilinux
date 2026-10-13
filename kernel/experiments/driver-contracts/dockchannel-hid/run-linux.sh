#!/bin/sh
# Execute only in the isolated Linux lab, never on the macOS host.
set -eu
cd "$(dirname "$0")"
cc=${CC:-cc}
flags='-std=gnu11 -g -O1 -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare -fsanitize=address,undefined -fno-omit-frame-pointer'
$cc $flags -Ibaseline test_parser.c -o test-baseline
$cc $flags -Ipatched test_parser.c -o test-patched
export ASAN_OPTIONS=detect_leaks=1:halt_on_error=1
export UBSAN_OPTIONS=halt_on_error=1:print_stacktrace=1
mkdir -p results
$cc --version > results/compiler.txt
printf '%s\n' "$flags" > results/compiler-flags.txt
# Each baseline case independently reproduces its defect. ASan catches memory
# access failures; semantic assertions catch malformed input being accepted.
for case in short_firmware unterminated_name short_gpio empty_product empty_event short_body unaligned_body bad_iface bad_subheader allocation_rearm
do
    if ./test-baseline "$case" > "results/baseline-$case.txt" 2>&1; then
        printf 'FAIL: baseline unexpectedly accepted test %s\n' "$case"
        exit 1
    fi
    printf 'baseline reproduced: %s\n' "$case"
done
./test-patched all > results/patched.txt
cat results/patched.txt
if [ "${1:-}" = --benchmark ]; then
    bench_flags='-std=gnu11 -g -O2 -Wall -Wextra -Wno-unused-parameter -Wno-sign-compare'
    printf '%s\n' "$bench_flags" > results/benchmark-compiler-flags.txt
    uname -srm > results/benchmark-os.txt
    $cc $bench_flags -Ibaseline '-DTEST_VARIANT="baseline"' test_parser.c -o bench-baseline
    $cc $bench_flags -Ipatched '-DTEST_VARIANT="patched"' test_parser.c -o bench-patched
    : > results/parser-benchmark.jsonl
    for variant in baseline patched patched baseline baseline patched; do
        ./bench-$variant bench 10000000 >> results/parser-benchmark.jsonl
    done
    cat results/parser-benchmark.jsonl
fi
