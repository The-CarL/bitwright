# Apple-1-inspired gate-built computer

Approved direction, 2026-10-01. This supersedes the bespoke 51-opcode CPU,
32 KiB/16 KiB map, and stock-TTY-only terminal proposal. Historical M0 reports
remain records of those experiments, not descriptions of the current target.

## Observable goal

Reset into firmware, select an assembled program file, transfer it through the
keyboard interface, inspect its bytes in RAM, and run it on the circuit CPU.
Load a second program without changing the circuit or ROM. At least one program
must read text input, compute a result using loops/subroutines, and return to the
monitor. Assembly source is assembled on the host; the machine executes bytes.

## Fidelity contract

Target the documented original NMOS 6502 instruction semantics and addressing
modes. Partial opcode support is an intermediate milestone, not 6502 conformance.
Decimal arithmetic, flags, stack order, wraparound and interrupt behavior need
explicit tests before declaring compatibility. Undocumented instructions are
outside the target and must produce a visible fault. No cycle-perfect bus,
transistor-level, analog-video or MHz-performance claim follows from software
compatibility. Record known deviations rather than concealing them in firmware.

The Apple-1 is the historical reference, not a claim that this project reproduces
every chip or electrical characteristic. Its original packaged CPU is replaced
by our inspectable hierarchical gate circuits. Our original monitor may be larger
than Wozniak's monitor. Using a modern host file feeder is a declared convenience.

## Construction boundary

Build selectors, decoders, arithmetic, registers, counters, CPU control, device
registers, terminal cursor/wrap/scroll and character-to-pixel generation from
gates. No built-in arithmetic, register, counter, mux, comparator or decoder.
No control ROM or Java CPU. Native subcircuits are abstractions we construct.

The CPU uses gate-built latches and flip-flops, including its register banks.
Single-bit D flip-flops remain a disclosed foundation in the console, and bulk
RAM/ROM remain foundations throughout the machine. Program and font ROM contain
data/software, never hidden ALU or instruction-control tables. Native feedback
capture/hold/reset tests and instruction comparisons verify the CPU storage.
The initial asserted reset is necessary to establish defined gate feedback.

The keyboard bridge represents an external ASCII keyboard: characters, valid,
acknowledgement and reset, including carriage return and Escape. Machine-side
latching, status and address decoding live in circuits. A bounded host queue
only crosses the event/simulation boundary. Overflow and file pacing are explicit.

The pixel bridge retains and displays circuit-supplied pixels. It owns no font,
cursor, terminal scrolling, program execution or machine RAM. The stock Keyboard
and TTY remain regression fixtures; they are not the final terminal implementation.

## Initial memory and development targets

Use 8-bit data and 16-bit addresses. Begin with 4 KiB RAM at 0000-0FFF, an
Apple-1-style console at D010-D013, and a 4 KiB firmware window at F000-FFFF.
The larger firmware window is a Bitwright difference, not an original Apple-1
specification. Reset fetches the vector at FFFC/FFFD. Preserve RAM on warm reset;
firmware initializes its own workspace. Reserved addresses read FF and ignore
writes. Decode and returned-data selection are gates.

The terminal target is 40 columns by 24 rows with a separate character store.
Character storage/font ROM are permitted memory foundations. Digital pixel
generation may differ from the original display's shift-register/composite-video
implementation; document that difference and measure throughput.

## Source material

- [Original Apple-1 manual, hardware](https://mirrors.apple2.org.za/www.chez.com/apple1/Apple1project/Docs/Apple1/Apple%201%20Manual%20-%20Page%201.htm)
- [Original monitor interaction](https://mirrors.apple2.org.za/www.chez.com/apple1/Apple1project/Docs/Apple1/Apple%201%20Manual%20-%20Page%203.htm)
- [1976 programming manual transcription](https://syncopate.us/books/Synertek6502ProgrammingManual.html)
- [Pinned simulator gate-delay documentation](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/resources/doc/en/html/guide/prop/delays.html)

## Evidence for the demonstration

Publish native circuits, source generators, an independent instruction reference
model, tests that detect deliberate faults, assembly sources, load records,
execution traces and measured performance. Inspect registers and bus transactions
while programs run. Demonstrating Astra means an inspectable, reproducible result;
generated artifacts and a plausible-looking terminal alone are not sufficient.
