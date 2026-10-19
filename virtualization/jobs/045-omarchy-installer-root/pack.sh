# pack.sh: stage 3 of job 045, sourced by run.sh. The RAM root as a newc cpio (job 039's
# packing: sorted names, --reproducible), zstd-compressed; sizes, and the upload time through
# the m1n1 proxy at the measured rate against the launcher's limits. With VARIANTS=1, also how
# much a root pruned of what a RAM root never reads (documentation, translations, headers,
# static libraries) would save.

# The launcher's omarchy profile (native/boot/launch.py), which delivers this root: a 900 s deadline and a
# 3 GiB ProxyUtils heap for kernel, DT and initrd. The rate is attempt 22's, the only upload of this size:
# 2,382,558,042 bytes in 456.5 s (native/boot/stage-b-2026-10-18-attempt22-result.md).
PROXY_BPS=5220000
DEADLINE_S=900
HEAP_BYTES=3221225472
# The package the root is for: its Image (the header's image_size is what the launcher allocates,
# 2 MiB-aligned) and the Stage-B DT the launcher uploads with it.
IMAGE_BYTES=$(stat -c %s "$KERNEL")
IMAGE_MEM=$(od -An -t u8 -j 16 -N 8 "$KERNEL" | tr -d ' ')
DTB_BYTES=$(stat -c %s "$(dirname "$KERNEL")/t6050-j716c-stage-b.dtb")

# cpio_of ROOT OUT: newc cpio of ROOT, names sorted, inode and device numbers renumbered
cpio_of() { ( cd "$1" && find . -mindepth 1 -printf '%P\n' | LC_ALL=C sort | cpio --quiet -o -H newc --reproducible ) > "$2"; }
# zst NAME CPIO ARGS...: compress into $Z/NAME.zst (the host-side output directory: the cpio
# fills the tmpfs), report size, compression time and one-thread decompression time (the kernel
# decompresses on one CPU). --ultra levels run on six threads to bound their memory.
zst() {
    local name=$1 in=$2; shift 2
    local t0 t1 t2 threads=-T0
    case " $* " in *" --ultra "*) threads=-T6 ;; esac
    t0=$(date +%s.%N)
    zstd -q $threads "$@" -c "$in" > "$Z/$name.zst"
    t1=$(date +%s.%N)
    zstd -q -d -T1 --long=31 -c "$Z/$name.zst" > /dev/null
    t2=$(date +%s.%N)
    printf '%-14s zstd %-26s bytes %11d  compress_s %7s  decompress_1thread_s %6s\n' "$name" "$*" \
        "$(stat -c %s "$Z/$name.zst")" "$(calc "$t1 - $t0")" "$(calc "$t2 - $t1" 2)" >> "$OUT/compression.txt"
}
# fit BYTES: the launcher's upload of Image + initrd + DT at the proxy rate, and the heap check
fit() {
    local b=$1
    local total=$((IMAGE_BYTES + b + DTB_BYTES))
    local heap_left=$((HEAP_BYTES - 65536 - 512 - 2097152 - IMAGE_MEM - 65536 - DTB_BYTES))
    printf 'initrd %d bytes: upload %d bytes, %s s at %.2f MB/s (deadline %d s: %s); m1n1 heap room for the initrd about %d bytes (%s)\n' \
        "$b" "$total" "$(calc "$total / $PROXY_BPS")" "$(calc "$PROXY_BPS / 1000000" 2)" "$DEADLINE_S" \
        "$(awk -v t="$total" -v r="$PROXY_BPS" -v d="$DEADLINE_S" 'BEGIN {print (t / r < d) ? "fits" : "exceeds"}')" \
        "$heap_left" "$( [ "$b" -le "$heap_left" ] && echo fits || echo exceeds)"
}

stage_pack() {
    T=/run/ilinux-045
    Z=$OUT/build
    mkdir -p "$T"
    mountpoint -q "$T" || mount -t tmpfs -o size=9G,mode=0755 tmpfs "$T"
    rm -f "$T"/*.cpio "$Z"/*.zst
    log "pack"
    # The root unpacks into a tmpfs, which holds each file in whole pages: 16 KiB on the M5.
    { echo "root_bytes $(du -sb --apparent-size "$C" | cut -f1)"
      echo "root_files $(find "$C" -mindepth 1 | wc -l)"
      echo "root_bytes_in_16k_pages $(find "$C" -type f -printf '%s\n' | awk '{b += int(($1 + 16383) / 16384) * 16384} END {printf "%d", b}')"
    } > "$OUT/sizes.txt"
    find "$C" -xdev -type f -size +4M -printf '%s %P\n' | sort -rn | awk 'NR <= 60' > "$OUT/build/largest-files.txt"
    du -sb --apparent-size "$C"/usr/lib/* "$C"/usr/share/* "$C"/usr/bin "$C"/opt/* "$C"/var/lib/* 2>/dev/null |
        sort -rn | awk 'NR <= 60 {printf "%9.1f MiB  %s\n", $1 / 1048576, $2}' | sed "s#$C##" > "$OUT/build/size-top-dirs.txt"
    cpio_of "$C" "$T/ramroot.cpio"
    echo "cpio_bytes $(stat -c %s "$T/ramroot.cpio")" >> "$OUT/sizes.txt"
    : > "$OUT/compression.txt"
    if [ -n "${ZSTD_FINAL:-}" ]; then   # out/job.env: one given level only (test iterations)
        FINAL_ARGS=$ZSTD_FINAL
    elif [ "$FAST" = 1 ]; then
        FINAL_ARGS="-3"
    else
        zst l3 "$T/ramroot.cpio" -3
        zst l19long "$T/ramroot.cpio" -19 --long=27
        FINAL_ARGS="--ultra -22 --long=27"
    fi
    zst final "$T/ramroot.cpio" $FINAL_ARGS
    mv "$Z/final.zst" "$OUT/ramroot.cpio.zst"
    (cd "$OUT" && sha256sum ramroot.cpio.zst > ramroot.cpio.zst.sha256)
    size=$(stat -c %s "$OUT/ramroot.cpio.zst")
    { echo "zst_bytes $size"
      echo "zst_args $FINAL_ARGS"
      fit "$size"; } >> "$OUT/sizes.txt"
    if [ "$FAST" != 1 ] && [ -z "${ZSTD_FINAL:-}" ]; then
        for n in l3 l19long; do fit "$(stat -c %s "$Z/$n.zst")" | sed "s/^/$n: /"; done >> "$OUT/sizes.txt"
    fi
    rm -f "$T/ramroot.cpio" "$Z"/l*.zst
    cat "$OUT/compression.txt" "$OUT/sizes.txt"

    [ "$VARIANTS" = 1 ] || return 0
    # Variant "docs": what job 039's pruning would remove that no Omarchy program reads at run
    # time (pacman's database, Python and Perl stay: Omarchy uses them). Measured, not delivered.
    log "variant: without documentation, translations, headers and static libraries"
    local V=$W/@variant
    [ -d "$V" ] && { btrfs subvolume list -o "$V" | awk '{print $NF}' | sort -r | while read -r sv; do btrfs subvolume delete "$W/$sv" > /dev/null; done; btrfs subvolume delete "$V" > /dev/null; }
    btrfs subvolume snapshot "$C" "$V" > /dev/null
    rm -rf "$V"/usr/share/{doc,man,info,gtk-doc,help,devhelp,gir-1.0,vala,aclocal} \
           "$V"/usr/include "$V"/usr/lib/pkgconfig "$V"/usr/share/pkgconfig "$V"/usr/lib/cmake
    find "$V"/usr/share/locale -mindepth 1 -maxdepth 1 -type d ! -name 'en*' -exec rm -rf {} +
    find "$V"/usr/lib -name '*.a' -type f -delete
    { echo "variant_docs_root_bytes $(du -sb --apparent-size "$V" | cut -f1)"; } >> "$OUT/sizes.txt"
    cpio_of "$V" "$T/variant.cpio"
    zst variant-docs "$T/variant.cpio" -19 --long=27
    fit "$(stat -c %s "$Z/variant-docs.zst")" | sed 's/^/variant-docs (zstd -19 --long=27): /' >> "$OUT/sizes.txt"
    rm -f "$T/variant.cpio" "$Z/variant-docs.zst"
    btrfs subvolume delete "$V" > /dev/null
    tail -3 "$OUT/sizes.txt"
}
