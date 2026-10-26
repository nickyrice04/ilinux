/* SPDX-License-Identifier: MIT */
/* Original data-first layout; relink the unchanged hash-pinned 31AC sources. */
OUTPUT_ARCH(aarch64)
ENTRY(native_entry)
PHDRS { data PT_LOAD FLAGS(6); late PT_LOAD FLAGS(5); boot PT_LOAD FLAGS(5); }
SECTIONS {
    native_image_base = DEFINED(visible_image_base) ? visible_image_base : 0;
    . = native_image_base + 0x4000;
    .data : { KEEP(*(.owned)) } :data
    ASSERT(. == native_image_base + 0x10000, "owned extent changed")
    .late : { KEEP(*(.late)) . = 0x4000; } :late
    ASSERT(. == native_image_base + 0x14000, "normal executable extent changed")
    .boot : {
        KEEP(*(.boot.entry))
        . = 0x800;
        KEEP(*(.boot.vectors))
        . = 0x2000;
        *(.text*) *(.rodata*)
        . = 0x10000;
    } :boot
    native_image_end = .;
    ASSERT(. == native_image_base + 0x24000, "payload extent changed")
    ASSERT(SIZEOF(.late) == 0x4000, "unexpected normal executable extent")
    ASSERT(SIZEOF(.data) == 0xc000, "unexpected data")
    ASSERT(SIZEOF(.boot) == 0x10000, "unexpected boot executable extent")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
