# Primitive policy

Allow Boolean gates, wiring, splitters, constants, pins/probes, clocks and native subcircuits built from these. Construct selectors, decoders, comparators, arithmetic, registers, counters and instruction control. Prohibit built-in CPU/ALU/adder/mux/decoder/comparator/register/counter, Java instruction execution, and ROM control/ALU lookup tables.

The CPU goes down to gate-built latches and flip-flops: its native library contains no built-in memory components. Registers compose these storage cells with gate-built enables and selection. Initial reset establishes a defined state in the feedback circuits. The console uses disclosed single-bit D flip-flops; bulk RAM/ROM are foundations. ROM may store firmware and glyph data, never hidden CPU control. A tiny gate-memory experiment can illustrate storage scaling without making thousands of feedback cells a prerequisite for program memory.

The console host only captures ASCII, feeds files through the input handshake, and retains/displays circuit-supplied pixels. Input registers, address decode, cursor, font lookup, wrap/scroll and execution belong to circuits. A bounded host queue crosses the event/simulation boundary and reports overflow.

Stock Keyboard/TTY remain regression fixtures; the mouse library stays an optional experiment. Recursive audit checks all native libraries, including unused definitions, a strict host-class/component allowlist, missing dependencies and nonportable paths. A component allowlist cannot by itself prove correct ROM purpose; source review also matters.

Reference: [simulator gate-delay limits](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/resources/doc/en/html/guide/prop/delays.html).
