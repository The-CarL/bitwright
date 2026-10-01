# Architecture status

This is the approved v1 target, amended on **2026-10-01** to keyboard, CPU, and
text monitor/basic terminal through stock TTY. It is not a claim that a computer
has been built. M0 must prove native artifacts, tests, storage/loading, and stock
Keyboard-to-TTY desktop behavior before CPU expansion. Mouse/graphics issues are
outside that gate. M0 remains open.

- [Primitive boundary](primitives.md): the foundations and host-adapter exception.
- [ISA](isa.md) and [opcode specification](isa.json): the approved instruction contract.
- [Memory and I/O](memory-and-io.md): the address map, boot behavior, and target device boundary.
- [Clock and control](control.md): datapath, transactions, reset, and observation points.
- [Milestones](../docs/roadmap.md): demonstrations and acceptance evidence.

The data path is 8 bits; byte addresses are 16 bits. An 8-bit address space is only
256 bytes, while 12 bits gives 4 KiB but still requires two-byte absolute operands.
Sixteen bits avoids banking within a 64 KiB address space and supports the chosen
RAM, ROM, and device map. The extra address-register and incrementer gates are an
explicit cost of this choice.

There are no interrupts, DMA, hardware multiplication/division, memory banking,
operating system, mouse, pixel graphics, framebuffer, or custom Java host bridge
in the v1 target. A complete demonstration consists of the basic terminal monitor
with help, memory dump/edit, and run commands, plus an arithmetic example and a
memory test.

The present entry `.circ` and candidate ZIP still contain the earlier mouse and
canvas experiment. Its implementation and measured evidence are preserved; a
focused stock-Keyboard/TTY artifact and package remain implementation work.
M5 is reserved for a deferred optional extension. M6 proceeds from M4 without M5.
