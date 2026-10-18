# elfcheck.sh: ELFCHECK=1 in out/job.env. Static facts about the RAM root ($C), changes nothing:
#  * every ELF file against 16 KiB pages (job 039's elf_page_check.py, read-only from the repo):
#    loadable segments a 16 KiB-page kernel cannot map, allocators with a build-time page size;
#  * the Chromium-based programs (a Chromium or Electron runtime: chrome-sandbox, the crashpad
#    handler, libffmpeg.so, resources/app.asar), with their owning packages;
#  * the size of the package cache (what the install downloaded).
stage_elfcheck() {
    local D=$OUT/elfcheck f
    rm -rf "$D"; mkdir -p "$D"
    python3 -I /mnt/ilinux/virtualization/jobs/039-omarchy-ram-root/elf_page_check.py "$C" > "$D/elf-16k-check.txt" 2>&1 || true
    head -4 "$D/elf-16k-check.txt"
    find "$C" -xdev \( -name chrome-sandbox -o -name chrome_crashpad_handler -o -name libffmpeg.so \
        -o -name 'app.asar' -o -name 'libcef.so' -o -name 'libQt6WebEngineCore.so*' \) -printf '%P\n' 2>/dev/null |
        sort > "$D/chromium-based-files.txt"
    while read -r f; do
        printf '%s\t%s\n' "$(pac "$C" -Qoq "$C/$f" 2>/dev/null || echo '?')" "$f"
    done < "$D/chromium-based-files.txt" > "$D/chromium-based-owners.txt"
    cat "$D/chromium-based-owners.txt"
    { du -sb "$W/cache" | cut -f1; ls "$W/cache" | grep -c '\.pkg\.tar\.[a-z]*$'; } > "$D/package-cache.txt"
    cat "$D/package-cache.txt"
    # the agent wrappers omarchy-provision-user wrote (mise.sh), and what one of them runs
    ls -la "$C/home/omarchy/.local/bin" > "$D/user-local-bin.txt" 2>&1
    cat "$C/home/omarchy/.local/bin/claude" > "$D/claude-wrapper.txt" 2>&1
    ls "$C/home/omarchy/.config/omarchy/hooks/post-update.d" > "$D/post-update-hooks.txt" 2>&1
}
