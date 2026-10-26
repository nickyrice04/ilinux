/* SPDX-License-Identifier: MIT */
OUTPUT_ARCH(aarch64)
ENTRY(native_entry)
PHDRS { reserved PT_LOAD FLAGS(4); late PT_LOAD FLAGS(5); boot PT_LOAD FLAGS(5); }
SECTIONS {
    native_image_base = DEFINED(immutable_image_base) ? immutable_image_base : 0;
    . = native_image_base + 0x4000;
    .reserved : { KEEP(*(.reserved)) } :reserved
    ASSERT(. == native_image_base + 0x58000, "reserved SPTM extent changed")
    .late : { KEEP(*(.late)) . = 0x4000; } :late
    ASSERT(. == native_image_base + 0x5c000, "normal executable extent changed")
    .boot : {
        KEEP(*(.boot.entry))
        . = 0x800;
        KEEP(*(.boot.vectors))
        . = 0x1000;
        KEEP(*(.boot.body))
        . = 0x4000;
    } :boot
    native_image_end = .;
    ASSERT(. == native_image_base + 0x60000, "payload extent changed")
    ASSERT(SIZEOF(.reserved) == 0x54000, "unexpected reserved extent")
    ASSERT(SIZEOF(.late) == 0x4000, "unexpected normal executable extent")
    ASSERT(SIZEOF(.boot) == 0x4000, "unexpected boot executable extent")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
