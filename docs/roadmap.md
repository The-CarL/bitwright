# Demonstrable roadmap

The approved scope was narrowed on **2026-10-01** to a CPU, keyboard, and text
monitor/basic terminal using stock TTY. CPU/ISA/storage decisions remain intact.
Mouse, pixel graphics, framebuffer scanning, and a custom Java bridge are outside
v1. The older M0 canvas artifact and its evidence are retained separately under
`experiments/mouse-canvas/`. The focused Keyboard-to-TTY entry is implemented;
revised-package and desktop acceptance remain in progress.

M0 remains the first gate. Resolve native-artifact, test-runner, storage/loading,
and keyboard/TTY desktop issues before expanding the CPU. Mouse and drag findings
no longer block that gate. GitHub descriptions and dependencies have been
synchronized with this narrower scope; the deferred M5 issue remains open.

| Milestone | Working demonstration | Acceptance evidence |
| --- | --- | --- |
| M0 / `v0.0.1` — Feasibility bench | Native logic/storage, memory loading, and stock Keyboard-to-TTY, without a CPU | Relocated offline open; save/reopen; passing stateful vectors; intentional failure rejected; bounded RAM harness; real text entry, refocus, pause/resume, and reset; limitations recorded |
| M1 / `v0.1` — Logic workbench | Interactive gate-built muxes, adders, registers, counters, flags, and ALU | Complete small truth tables; exhaustive 8-bit ALU operand pairs, with both carry inputs; reset/load/hold priority; carry/borrow/overflow; counter boundaries; recursive primitive audit |
| M2 / `v0.2` — First stored program | CPU runs a ROM loop and writes a checked RAM result | Fetch/operands across byte boundaries; PC rollover; RAM/ROM decode including reserved addresses; one write per transaction; no reset/halt writes; bounded completion |
| M3 / `v0.3` — Complete ISA and loading | Assembler programs use pointers, RAM, stack, and nested calls | Every encoding; flag behavior; nested CALL/RET and byte order; stack wrap; illegal opcode; assembler errors; reference-model comparison at retirement and for ordered writes |
| M4 / `v0.4` — Terminal computer | Boot banner and basic terminal monitor with help, memory dump/edit, and run commands | Repeatable boot; keyboard FIFO empty/full/wrap/reset and backpressure without dropping its head; explicit acknowledgement; ASCII parsing; RAM program returns through CALL/trampoline/RET; golden transcript |
| M5 / former `v0.5` — Deferred extension | Reserved for optional mouse/graphics work outside v1 | No v1 acceptance gate or blocking dependency; preserve earlier experiment and findings |
| M6 / `v1.0` — Complete release | Download/open/run text computer, terminal monitor, arithmetic demo, and memory test | M4 accepted; regressions; clean-folder offline run; fresh-user instructions; platform smoke checks; measured performance and limitations; no required mouse/custom bridge |

Dependencies are **M0 → M1 → M2 → M3 → M4 → M6**. M5 is deferred and does not block
M6.

Before M4 firmware, define the monitor scratch-memory allocation and allowed load
range. The run command uses `CALL run_trampoline`, the trampoline uses `JMP X`,
and a user program returns via `RET`. These are software conventions on the
approved ISA, not new instructions or an implemented monitor.

## Amended M0 gate

1. Keep a manually maintained native fixture and generated equivalent containing
   a gate function and one-bit load-enabled storage cell; save/reopen through
   Logisim.
2. Run combinational and retained-state sequential vectors. Prove that an
   incorrect expected value fails the wrapper; reject missing summaries, errors,
   incomplete runs, and timeout.
3. Load a tiny RAM image and stop a bounded clocked harness on a known result.
4. Prepare a focused stock Keyboard-to-TTY entry with no required mouse, pixel
   display, or custom Java bridge. Verify actual desktop typing and re-entry
   after changing focus, pause/resume, and reset.
5. Open the focused package after relocation with networking disabled, then save
   a disposable copy and close/reopen it. Record versions, checksums, outcomes,
   host-keyboard buffer limitations, and text responsiveness.

The first live `HELLO BITWRIGHT` entry remains valid evidence. The later keyboard
refocus attempt produced no new text and has no established cause; investigate it
against the focused bench. Passing the earlier Java/mouse tests is not a new M0
requirement, and retaining them does not make M0 complete.

The primary entry is now the focused stock Keyboard/TTY bench. Default tooling
is being validated against that entry; the optional canvas has separate commands.
Use the [focused evidence report](evidence/m0-keyboard-2026-10-01.md) for current
acceptance. Older archives and the historical report retain their original
contents; the historical mouse tests do not close the revised M0 gate.

## Testing and performance policy

Vector wrappers drive an ordinary clock input with setup and low/high phases.
Sequential tests must retain state. The packaged 5.0.0 launcher returned zero for
a deliberately failing vector, so inspect result counts as well as process
status. Linux vector CI needs a virtual display because vector execution
initializes Swing.

System tests use exact `halt` output naming, a separate pass/signature output,
watchdogs, and ordered traces. They must terminate with a known expected result.
Broaden testing only after a relevant change or unresolved failure.

Publish the reference machine, JVM, circuit size, benchmark program, wall time,
cycles/second, instructions/second, and keyboard-to-visible-text latency.
Under 250 ms ordinary terminal response remains a measurement target, not a
performance guarantee. Graphics throughput is outside v1 acceptance.
