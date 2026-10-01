# Demonstrable roadmap

The architecture is approved. M0 is the first implementation gate, and no later
milestone is considered complete merely because its specification or issue exists.
Resolve any native-artifact, test-runner, or real mouse/display failure before
expanding the CPU.

| Milestone | Working demonstration | Acceptance evidence |
| --- | --- | --- |
| M0 / `v0.0.1` — Feasibility bench | Native logic/storage, memory loading, text, pixels, and mouse, without a CPU | Relocated offline open; save/reopen; passing stateful vectors; an intentional failure rejected; bounded RAM harness; stable mouse packets until acknowledgement; actual host input and pixel output; limitations recorded |
| M1 / `v0.1` — Logic workbench | Interactive gate-built muxes, adders, registers, counters, flags, and ALU | Complete small truth tables; exhaustive 8-bit ALU operand pairs, with both carry inputs; reset/load/hold priority; carry/borrow/overflow; counter boundaries; recursive primitive audit |
| M2 / `v0.2` — First stored program | CPU runs a ROM loop and writes a checked RAM result | Fetch/operands across byte boundaries; PC rollover; RAM/ROM decode; one write per transaction; no reset/halt writes; bounded completion |
| M3 / `v0.3` — Complete ISA and loading | Assembler programs use pointers, RAM, stack, and nested calls | Every encoding; flag behavior; nested CALL/RET and byte order; stack wrap; illegal opcode; assembler errors; reference-model comparison at retirement and for ordered writes |
| M4 / `v0.4` — Terminal computer | Boot banner and interactive memory monitor | Repeatable boot; keyboard FIFO empty/full/wrap/reset/overflow; explicit acknowledgement; ASCII parsing; load/edit/run RAM program; golden transcript |
| M5 / `v0.5` — Mouse canvas | A program paints from real mouse input and returns to the terminal | Corners/colors/clear/repeated writes; whole packets; drag/release; focus loss; overflow; pause/resume; plot traces and visible output |
| M6 / `v1.0` — Complete release | Download/open/run computer, monitor, arithmetic demo, memory test, and drawing demo | Regressions; clean-folder offline run; fresh-user instructions; platform smoke checks; published performance and limitations |

## M0 gate

Keep the first bench deliberately small:

1. A manually maintained native fixture and generated equivalent contain a gate
   function and one-bit load-enabled storage cell. Save/reopen through Logisim.
2. Run passing combinational and sequential vectors, then prove that an incorrect
   expected value fails the wrapper. Reject missing summaries, errors, and timeout.
3. Load a tiny RAM image and stop a bounded clocked harness on a known result.
4. Transfer stock Keyboard input to TTY, and write/clear stock RGB Video pixels.
5. Exercise the minimal custom canvas's pixel commands and real mouse
   press/drag/release packets; check stability until acknowledgement.
6. Package for relocation and offline use. Record checksums, simulator/JDK,
   round-trip behavior, focus requirements, host buffering, and responsiveness.

The custom bridge must ignore the poker adapter's synthetic press without a
button ID and process the original event forwarded by the Poke tool. Verify button
identity through the complete callback path, then record actual desktop behavior.
Hover is outside the interface supported by the pinned `InstancePoker` API.

M0 acceptance requires the real desktop path. Parser/unit tests and a successful
Java build alone cannot prove the mouse, native save/open, or visible pixel path.
Only publish M0 as complete once its evidence report meets all gates.

## Testing and performance policy

Vector wrappers drive an ordinary clock input with setup and low/high phases.
Sequential tests must retain state; a set of unrelated combinational vectors is
not equivalent. The 5.0.0 launcher may exit successfully despite failed vectors,
so inspect the result text as well as process status. Linux vector CI needs a
virtual display unless the chosen packaged path has been independently verified
to be headless.

System tests use exact `halt` output naming, a separate pass/signature output,
watchdogs, and ordered traces. They must terminate with a known expected result.
Broaden testing only after a relevant change or unresolved failure.

Publish the reference machine, JVM, circuit size, benchmark program, wall time,
cycles/second, instructions/second, and input-to-visible latency. Under 250 ms
ordinary typing/drawing response is a target to measure. No full-frame animation
rate is promised.
