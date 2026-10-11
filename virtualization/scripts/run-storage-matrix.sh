#!/bin/bash
# Boot the test VM once per storage configuration (job 005) and collect
# results.  Writes ~4 GiB per configuration to a 16 GB sparse data disk.
set -euo pipefail
P="$(cd "$(dirname "$0")/../.." && pwd)"
I=$P/virtualization/images/alarm; J=$P/virtualization/jobs/005-vzstorage
[ -f $I/data.img ] || mkfile -n 16g $I/data.img
run() {  # label vzrun-flags...
  local label=$1; shift
  echo "$label" > $J/config.txt
  perl -e 'alarm shift; exec @ARGV' 900 $P/virtualization/bin/vzrun --cpus 8 --mem 8 \
    --kernel $I/Image --cmdline "$(cat $I/cmdline)" --disk $I/root.img --disk $I/data.img \
    --share $J:job "$@" < /dev/null > /dev/null 2>&1 || echo "boot $label exited $?"
  tail -1 $J/out/run.log
}
run virtio-auto-full  --disk-cache automatic --disk-sync full
run virtio-auto-fsync --disk-cache automatic --disk-sync fsync
run virtio-cached-none --disk-cache cached --disk-sync none
run virtio-uncached-full --disk-cache uncached --disk-sync full
run nvme-auto-full --nvme --disk-cache automatic --disk-sync full
run nvme-cached-none --nvme --disk-cache cached --disk-sync none
