#!/bin/bash
set -euo pipefail
mode=$(cat /mnt/job/out/mode 2>/dev/null || echo build)
case "$mode" in
  build|bench) exec /bin/bash "/mnt/job/$mode.sh" ;;
  parallel) ILINUX_VM_CASES=4 exec /bin/bash /mnt/job/bench.sh ;;
  blur) ILINUX_VM_CASES=5 exec /bin/bash /mnt/job/bench.sh ;;
  *) exit 2 ;;
esac
