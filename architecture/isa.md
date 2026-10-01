# Bitwright v1 instruction set

Status: approved target; CPU and assembler implementation are later milestones.
[isa.json](isa.json) owns opcode assignments and instruction lengths. This document
owns behavioral semantics; changes to either require a coordinated compatibility
review and tests.

## Encoding

The first byte is an opcode. Operands occupy zero, one, or two following bytes.
Sixteen-bit operands are little-endian. Absolute addressing and conditional branch
targets are full 16-bit addresses. `[X]` addresses memory indirectly through X;
`JMP X` jumps to X without reading a pointer from memory. There is no relative,
indexed-displacement, or memory-indirect addressing in v1.

Within each row, consecutive opcodes correspond to the listed instructions:

| Opcodes | Instructions |
| --- | --- |
| `00–01` | `NOP`, `HLT` |
| `10–1B` | `LDA #8`, `LDA abs16`, `LDA [X]`, `STA abs16`, `STA [X]`, `LDX #16`, `INX`, `DEX`, `TAXL`, `TAXH`, `TXLA`, `TXHA` |
| `20–29` | `ADD #8`, `ADD abs16`, `ADC #8`, `ADC abs16`, `SUB #8`, `SUB abs16`, `SBC #8`, `SBC abs16`, `CMP #8`, `CMP abs16` |
| `30–38` | `AND #8`, `AND abs16`, `OR #8`, `OR abs16`, `XOR #8`, `XOR abs16`, `NOT A`, `SHL A`, `SHR A` |
| `40–49` | `JMP abs16`, `JMP X`, `JZ abs16`, `JNZ abs16`, `JC abs16`, `JNC abs16`, `JN abs16`, `JNN abs16`, `JV abs16`, `JNV abs16` |
| `50–57` | `CALL abs16`, `RET`, `PHA`, `PLA`, `PHF`, `PLF`, `CLC`, `SEC` |

All other opcodes enter a visible fault/halt state. PC and 16-bit pointer arithmetic
wrap modulo 65,536; byte arithmetic wraps modulo 256. Instruction fetch may cross
page and address-space boundaries. A fault/halt prevents subsequent writes until
reset, while exposing the offending opcode and instruction location.

## Registers and flags

- `A` is the 8-bit accumulator; `B` is an internal 8-bit operand temporary.
- `X` is a 16-bit pointer; `XL` and `XH` are its low and high bytes.
- `PC` and `MAR` are 16-bit program/address registers; `IR` and `SP` are 8 bits.
- Packed flag bits 0–3 are `C`, `Z`, `N`, `V`; packed bits 4–7 read as zero.

`TAXL`/`TAXH` copy A into the named X byte and preserve the other byte. `TXLA`/`TXHA`
copy the named X byte to A. `LDX` loads both X bytes. `INX`/`DEX` operate on all 16 bits.

| Instruction class | Flag effect |
| --- | --- |
| `ADD`, `ADC`, `SUB`, `SBC`, `CMP` | Set C/Z/N/V from the 8-bit result; CMP does not write A |
| `AND`, `OR`, `XOR`, `NOT` | Set Z/N; clear C/V |
| `SHL`, `SHR` | Logical shift by one, zero fill; C gets shifted-out bit, Z/N reflect result, V clears |
| `LDA`, `PLA`, `TXLA`, `TXHA` | Set Z/N from A; preserve C/V |
| `INX`, `DEX` | Set Z/N from the 16-bit result (N is bit 15); preserve C/V |
| `PLF` | Restore C/Z/N/V from bits 0–3; ignore upper bits |
| `CLC`, `SEC` | Clear/set C; preserve Z/N/V |
| All others, including `LDX` | Preserve flags |

Z means the relevant result is zero; N is its top bit. Addition carry means an
unsigned carry out. Subtraction carry means **no borrow**. `ADC` adds the incoming
C; `SBC` subtracts the operand and `1−C`. `ADD` and `SUB` ignore incoming C.
V indicates that the mathematical signed result is outside −128…127, including
the carry/borrow input where applicable. Conditional branches inspect only the
named flag; failed branches continue after their two operand bytes.

## Stack and subroutines

The stack occupies `0100–01FF`; reset sets `SP=FF`. Push writes to `0100 | SP`,
then decrements SP; pop increments SP, then reads. SP wraps modulo 256, with no
hardware stack-overflow fault. Software must respect the stack limit.

`CALL` pushes the address immediately following its operands, high byte then low
byte, and sets PC to its target. `RET` pops low then high and restores PC. `PHA`
pushes A; `PLA` pops A. `PHF` pushes the packed flags; `PLF` restores them. These
conventions permit nested calls and return addresses across page boundaries.

`HLT` stops advancement and memory/device writes; reset restarts execution.

## Software tool contract

The future assembler supports labels, constants, expressions, `.org`, `.byte`,
`.word`, and ASCII strings. It must emit an eight-bit `v2.0 raw` memory image,
listing, symbols, and a bank-origin/load manifest. Reject undefined or duplicate
labels, overlapping output, and out-of-range operands. An independent instruction
model checks retirement state and ordered writes; it is never the delivered CPU.
