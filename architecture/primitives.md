# Primitive-component boundary

Approved for the v1 computer:

| Layer | Allowed foundations | Logic Bitwright must build |
| --- | --- | --- |
| Combinational logic | Logic gates, wires, splitters, constants, pins, probes | Multiplexers, decoders, comparators, adders, ALU, bus selection |
| State | Single-bit D flip-flops | Register banks, enables, counters, stack pointer, controller state |
| Bulk storage | Built-in RAM and ROM arrays | Address decoding, write control, FIFO pointers/status |
| Simulation | Clock sources and test-wrapper input pins | Clock/reset distribution and state advancement policy |
| Host adapters | Stock Keyboard, TTY, RGB Video; documented source-available Java canvas bridge | CPU-visible device registers, acknowledgements, FIFO control |

Built-in CPU, ALU, adder, multiplexer, register, counter, comparator, and decoder
components are prohibited in machine logic. RAM/ROM is for program, data, or fonts;
lookup tables must not conceal an ALU or instruction controller. Use a hardwired
multicycle controller, not microcode ROM.

Keep host adapters visibly separate from machine logic. The custom canvas may
capture host events, retain rendered pixels, and queue host events across the UI
and simulation boundary. It must not execute instructions, decode CPU addresses,
run drawing algorithms, or implement the CPU-visible FIFO. A host queue and a
circuit FIFO are different buffers and must have separate documented capacity
and overflow behavior.

The component audit must follow every native library used by a machine project,
identify host exceptions explicitly, and reject unknown components until reviewed.
Test-only observation or stimulus components must be identified separately and
must not bypass the circuits under test.

A gate latch and tiny memory experiment are educational artifacts. The complete
computer does not depend on gate-feedback storage. Gate-built 32 KiB RAM alone
would require 262,144 storage bits before decoding/read selection, so bulk memory
is a deliberate practicality boundary.
