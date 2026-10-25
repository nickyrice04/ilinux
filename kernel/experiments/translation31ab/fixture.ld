/* SPDX-License-Identifier: MIT */
OUTPUT_ARCH(aarch64)
ENTRY(fixture_entry)
PHDRS { code PT_LOAD FLAGS(5); data PT_LOAD FLAGS(6); }
SECTIONS {
    . = 0x40480000;
    .text : { KEEP(*(.text.entry)) *(.text.probe) } :code
    .vectors ALIGN(2048) : { KEEP(*(.text.vectors)) } :code
    ASSERT(. <= 0x40483000, "fixture code exceeds reserved extent")
    . = 0x40483000;
    .capture : { KEEP(*(.capture)) } :data
    .tables (NOLOAD) : {
        fixture_l1 = .; . += 4096;
        fixture_l2 = .; . += 4096;
        fixture_l3 = .; . += 4096;
    } :data
    ASSERT(. == 0x40487000, "unexpected fixture geometry")
    /DISCARD/ : { *(.comment) *(.note*) }
}
