# GitHub backlog

Created from the approved architecture and synchronized with the **2026-10-01
keyboard/text-terminal scope amendment**. M0 remains open; mouse/graphics work is
deferred outside v1. Issue creation or an existing experimental artifact does not
mean an acceptance gate is complete. [Live milestones](https://github.com/The-CarL/bitwright/milestones)
track progress; [roadmap.md](roadmap.md) defines the current acceptance gates.

| Milestone | GitHub milestone | Issues |
| --- | --- | --- |
| M0 | [v0.0.1 — M0 Feasibility bench](https://github.com/The-CarL/bitwright/milestone/1) | [#1](https://github.com/The-CarL/bitwright/issues/1), [#2](https://github.com/The-CarL/bitwright/issues/2), [#3](https://github.com/The-CarL/bitwright/issues/3) |
| M1 | [v0.1 — M1 Logic workbench](https://github.com/The-CarL/bitwright/milestone/2) | [#4](https://github.com/The-CarL/bitwright/issues/4) |
| M2 | [v0.2 — M2 First stored program](https://github.com/The-CarL/bitwright/milestone/3) | [#5](https://github.com/The-CarL/bitwright/issues/5) |
| M3 | [v0.3 — M3 Complete ISA and loading](https://github.com/The-CarL/bitwright/milestone/4) | [#6](https://github.com/The-CarL/bitwright/issues/6), [#7](https://github.com/The-CarL/bitwright/issues/7) |
| M4 | [v0.4 — M4 Terminal computer](https://github.com/The-CarL/bitwright/milestone/5) | [#8](https://github.com/The-CarL/bitwright/issues/8) |
| M5 — deferred, outside v1 | [Deferred — M5 Mouse canvas (beyond v1)](https://github.com/The-CarL/bitwright/milestone/6) | [#9](https://github.com/The-CarL/bitwright/issues/9), open optional extension |
| M6 | [v1.0 — M6 Complete release](https://github.com/The-CarL/bitwright/milestone/7) | [#10](https://github.com/The-CarL/bitwright/issues/10), [#11](https://github.com/The-CarL/bitwright/issues/11) |

| Issue | Demonstration |
| --- | --- |
| [#1](https://github.com/The-CarL/bitwright/issues/1) | M0: Prove native circuit round trips and reliable automated tests |
| [#2](https://github.com/The-CarL/bitwright/issues/2) | M0: Validate stock keyboard input and text monitor |
| [#3](https://github.com/The-CarL/bitwright/issues/3) | M0: Package and document the relocatable offline feasibility bench |
| [#4](https://github.com/The-CarL/bitwright/issues/4) | M1: Build and verify the primitive logic workbench |
| [#5](https://github.com/The-CarL/bitwright/issues/5) | M2: Execute the first ROM program on the circuit CPU |
| [#6](https://github.com/The-CarL/bitwright/issues/6) | M3: Add the assembler, memory artifacts, and independent CPU model |
| [#7](https://github.com/The-CarL/bitwright/issues/7) | M3: Complete the ISA, stack, subroutines, and differential tests |
| [#8](https://github.com/The-CarL/bitwright/issues/8) | M4: Boot into an interactive terminal memory monitor |
| [#9](https://github.com/The-CarL/bitwright/issues/9) | Deferred beyond v1: M5 mouse and pixel canvas extension |
| [#10](https://github.com/The-CarL/bitwright/issues/10) | M6: Ship the reproducible offline computer and demonstration suite |
| [#11](https://github.com/The-CarL/bitwright/issues/11) | M6: Publish an evidence-led build journal and blog/Forge project |

Dependencies run **M0 → M1 → M2 → M3 → M4 → M6**. Release issue #10 depends on
terminal issue #8 and documentation issue #11, not mouse issue #9. M5 and GitHub
milestone 6 remain deferred and nonblocking; they have not been closed.

Issue #3 includes adapting the current entry/package to the focused keyboard/TTY
target without a required custom canvas JAR. That implementation is still pending:
the present entry circuit and ZIP retain the earlier optional experiment. Journal
work follows actual evidence and final documentation depends on M4, not M5.
Dates are not promised; releases follow acceptance criteria.
