/* SPDX-License-Identifier: MIT */
OUTPUT_ARCH(aarch64)
ENTRY(native_entry)
PHDRS { data PT_LOAD FLAGS(6); boot PT_LOAD FLAGS(5); late PT_LOAD FLAGS(5); }
SECTIONS {
    native_image_base = DEFINED(visible_image_base) ? visible_image_base : 0;
    . = native_image_base + 0x4000;
    .data : { KEEP(*(.owned)) } :data
    ASSERT(. == native_image_base + 0x10000, "owned extent changed")
    .boot : {
        KEEP(*(.boot.entry))
        . = 0x800;
        KEEP(*(.boot.vectors))
        . = 0x2000;
        *(.text*) *(.rodata*)
        . = 0x10000;
    } :boot
    .late : { KEEP(*(.late)) . = 0x4000; } :late
    native_image_end = .;
    ASSERT(. == native_image_base + 0x24000, "payload extent changed")
    ASSERT(SIZEOF(.data) == 0xc000, "unexpected data")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
