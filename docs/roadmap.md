# Apple-1 direction: demonstrable milestones

This supersedes the custom-ISA/stock-TTY roadmap. Existing M0 experiments are
retained as evidence, not a substitute for executing programs. Mouse is deferred.

| Milestone | Demonstration | Acceptance |
| --- | --- | --- |
| M0 | Native artifact/tool boundary | Failure detection, watchdog, RAM load, save/reopen, portable dependencies |
| M1 | Gates to arithmetic and state | Full-adder truth table, gate-latch/flip-flop reset/capture/hold, strict component audit |
| M2 | First stored program | Reset-vector fetch, real instruction execution, checked RAM result, one write per transaction |
| M3 | Documented 6502 and loading | All encodings in differential tests, ordered writes/flags/stack/addressing, interrupts/decimal boundaries; assembler errors |
| M4 | Interactive computer | Firmware loads bytes via ASCII, executes two interchangeable programs, returns to monitor; keyboard and circuit terminal tests |
| M5 | Optional mouse extension | Outside this target; does not block release |
| M6 | Reproducible demonstration | Relocated/offline package, desktop input/file-selection, saved/reopened behavior, readable hierarchy, performance and limitations |

Implemented artifacts must be distinguished from accepted milestones. Native
tests exercise real circuits; host reference-model tests do not establish native
CPU correctness by themselves. A CPU subset is an intermediate result only.
The CPU manifest describes implemented coverage and deliberate fidelity limits.
Merging a reviewed development candidate does not close M6 or declare a release;
remaining desktop, platform and performance acceptance stays tracked separately
in the [evidence report](evidence/apple1-2026-10-01.md#follow-up-2026-10-04).

## Final demonstration

Open the unchanged machine, reset into its monitor, load a .mon generated from
an assembly file, enter a digit, compute a result in CPU instructions and RAM,
then return to the monitor. Load another program without replacing the ROM.
Inspect registers, buses, ALU, decoder, gate storage and terminal logic.

The host adapter captures ASCII (including Escape/CR), queues files, and presents
raw pixels. It must not execute instructions, inject RAM, decode addresses or
render text. CPU/terminal source review and recursive component audit accompany
behavioral testing.

## Performance

Record simulator/JDK/host, primitive counts, actual cycles/s, file load time and
input-to-visible-pixel latency. Clock settings are requests, not measurements.
Gate-built CPU flip-flops increase simulation work; retain measured comparisons.
The pixel scan is digital and does not claim original analog video timing.

The independent reference model, negative verifier cases, native state/IO tests,
and deterministic regeneration are release requirements. Desktop and platform
acceptance must be reported separately from headless tests.
