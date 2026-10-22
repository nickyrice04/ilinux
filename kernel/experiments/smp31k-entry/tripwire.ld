/* Original fixed-offset linker script for offline assembly reproduction. */
ENTRY(cold_tripwire)
SECTIONS {
  . = 0xb00;
  .text : { *(.text) }
  cold_record = 0x90a80;
  /DISCARD/ : { *(.comment) *(.note*) }
}
