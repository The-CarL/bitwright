# Architecture status

This is the approved v1 target, not a claim that a computer has been built.
Implementation starts with the M0 feasibility bench. Integration failures found
there must be resolved before expanding the CPU.

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
or operating system in v1. The display bridge retains pixels; a circuit-scanned
framebuffer is outside v1. A complete demonstration consists of the boot monitor,
terminal, mouse-operated pixel canvas, arithmetic example, and memory test.
