# Memory and I/O

| Address | Meaning |
| --- | --- |
| 0000-0FFF | 4 KiB RAM; zero page 0000-00FF, stack 0100-01FF |
| D010 | Keyboard character, acknowledged when read |
| D011 | Keyboard status; bit 7 indicates ready |
| D012 | Display character/status; bit 7 indicates busy |
| D013 | Read zero; writes ignored |
| F000-FFFF | 4 KiB firmware window with original Bitwright monitor |
| FFFA-FFFF | NMI, reset and IRQ/BRK vectors within ROM |
| Other | Read FF; ignore writes |

This is Apple-1-inspired. The larger firmware, modern file feeder and digital display are differences. D011/D013 writes are ignored by the monitor-oriented PIA subset; full 6820 DDR/interrupt behavior is not claimed.

Gate-built MemoryMap decodes addresses and selects bytes using separate input/output buses. Warm reset preserves RAM; firmware initializes workspace and stack.

## Loading

Assembly is host source. The assembler emits executable bytes, images, symbols, listings and .mon deposit records. The file feeder supplies characters through the acknowledged keyboard path; firmware running on the circuit CPU parses them into RAM. No filesystem or hidden host execution. Direct Logisim RAM loading is a debugging aid, not firmware-loader acceptance. Native tests must compare loaded bytes and execute different programs in the unchanged circuit.

The monitor rejects deposits outside RAM and into its working storage: zero-page 0020-0027, stack 0100-01FF and line buffer 0200-024F. It checks each byte before writing; if a record crosses into a protected range, its accepted prefix remains in RAM. User programs are responsible for preserving that workspace when returning to the monitor. Example programs start at 0300. The line limit is 79 characters; generated records fit within it.

## Screen

Target 40x24 text. Circuits own character memory, cursor, wrap/scroll and glyph-to-pixel generation. Character RAM and font ROM are storage foundations. The host retains pixels only. No analog composite-video simulation is claimed.
