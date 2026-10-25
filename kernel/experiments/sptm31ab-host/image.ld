/* SPDX-License-Identifier: MIT */
OUTPUT_FORMAT(elf64-littleaarch64)
OUTPUT_ARCH(aarch64)
ENTRY(host_entry)
PROVIDE(host_image_base = 0);
PHDRS
{
    data PT_LOAD FLAGS(6);
    boot PT_LOAD FLAGS(5);
    late PT_LOAD FLAGS(5);
}
SECTIONS
{
    . = host_image_base + 0x4000;
    .data : { KEEP(*(.data.owned)) } :data
    ASSERT(SIZEOF(.data) == 0x8000, "owned data/stack geometry changed")
    . = host_image_base + 0xc000;
    .boot : {
        KEEP(*(.boot.entry))
        ASSERT(. <= host_image_base + 0xc800, "entry overlaps vector table");
        . = 0x800;
        KEEP(*(.boot.vectors))
        KEEP(*(.boot.fault))
        ASSERT(. <= host_image_base + 0xf000, "fatal recorder overlaps early transport");
        . = 0x3000;
        KEEP(*(.boot.transport))
        . = 0x4000;
    } :boot
    . = host_image_base + 0x10000;
    .text : {
        KEEP(*(.text.transport))
        . = 0x4000;
    } :late
    host_image_end = host_image_base + 0x14000;
    ASSERT(host_entry == host_image_base + 0xc000, "entry offset changed")
    ASSERT(host_vectors == host_image_base + 0xc800, "vector offset changed")
    ASSERT(host_stack_top == host_image_base + 0xc000, "stack offset changed")
    ASSERT(host_fixups_complete == host_image_base + 0xf000, "early transport moved")
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
}
