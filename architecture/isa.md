# ISA target

Target the documented original NMOS 6502: 8-bit A/X/Y/SP/status, 16-bit PC, little-endian operands, zero page, page-one stack and original addressing modes. This supersedes the 51-opcode Bitwright ISA and CALL/RET. Assembly uses JSR/RTS.

The assembler's full opcode table is not itself hardware conformance. Compare native registers, flags, PC/SP and ordered memory writes with the independent reference model. Test carry/borrow/overflow, page/zero-page wrap, stack wrap, nested calls, BRK/RTI, vectors and NMOS decimal arithmetic. Preserve indirect-JMP page wrap. Unsupported opcodes must fault.

Internal cycles are implementation-specific. No original bus-cycle, dummy-write, timing-sensitive-software or transistor-level compatibility is claimed.

Monitor firmware is original Bitwright software, not Wozniak's ROM. See software/monitor/monitor.asm for entries and services and demo sources for return conventions. Host assembly produces machine bytes and hexadecimal deposit records that firmware parses into RAM.

Reference: [1976 programming manual](https://syncopate.us/books/Synertek6502ProgrammingManual.html).
