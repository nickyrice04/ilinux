#!/bin/bash
set -euo pipefail
mode=$(cat /mnt/job/out/mode 2>/dev/null || echo bench)
case "$mode" in
    build|bench|integration|images|checks) exec /bin/bash "/mnt/job/$mode.sh" ;;
    *) echo 'unknown job055 mode' >&2; exit 2 ;;
esac
