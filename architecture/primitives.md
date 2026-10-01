# Primitive-component boundary

Approved for the keyboard/text-terminal v1 scope amended on 2026-10-01:

| Layer | Allowed foundations | Logic Bitwright must build |
| --- | --- | --- |
| Combinational logic | Logic gates, wires, splitters, constants, pins, probes | Multiplexers, decoders, comparators, adders, ALU, bus selection |
| State | Single-bit D flip-flops | Register banks, enables, counters, stack pointer, controller state |
| Bulk storage | Built-in RAM and ROM arrays | Address decoding, write control, FIFO pointers/status |
| Simulation | Clock sources and test-wrapper input pins | Clock/reset distribution and state advancement policy |
| Host adapters | Stock Keyboard and TTY | CPU-visible device registers, acknowledgements, keyboard FIFO control |

Built-in CPU, ALU, adder, multiplexer, register, counter, comparator, and decoder
components are prohibited in machine logic. RAM/ROM is for program, data, or fonts;
lookup tables must not conceal an ALU or instruction controller. Use a hardwired
multicycle controller, not microcode ROM.

Keep host adapters visibly separate from machine logic. Stock Keyboard captures
characters and stock TTY renders the text monitor. The CPU, address decoding,
device registers, and keyboard FIFO belong to circuits. The stock host keyboard
queue and machine FIFO are distinct buffers with separately documented capacity
and overflow behavior. No mouse, pixel display, framebuffer, or custom Java bridge
is required for v1.

The earlier stock RGB Video and custom Java canvas are preserved separately in
`experiments/mouse-canvas/`. Their circuits, code, tests, and historical evidence
belong to the optional experiment. Its explicit audit exceptions do not apply to
the primary Keyboard/TTY runtime or make mouse acceptance a v1 prerequisite.

The component audit must follow every native library used by a machine project,
identify host exceptions explicitly, and reject unknown components until reviewed.
Test-only observation or stimulus components must be identified separately and
must not bypass the circuits under test.

A gate latch and tiny memory experiment are educational artifacts. The complete
computer does not depend on gate-feedback storage. Gate-built 32 KiB RAM alone
would require 262,144 storage bits before decoding/read selection, so bulk memory
is a deliberate practicality boundary.
