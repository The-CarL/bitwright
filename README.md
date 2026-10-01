# Bitwright

**From gates to a terminal: building an inspectable 8-bit computer in Logisim-evolution.**

This personal project revisits an unfinished computer engineering undergraduate
ambition: build a complete computer from primitive circuits, with a CPU, memory,
keyboard, and text monitor. The v1 user interface is a basic terminal through
Logisim's stock TTY component.

## Current status

The approved v1 scope was narrowed on **2026-10-01** to keyboard, CPU, and a text
monitor/basic terminal. Mouse input, pixel graphics, a framebuffer, and a custom
Java bridge are outside v1. The CPU, ISA, RAM/ROM, and primitive policy remain.

**M0, the feasibility bench, is still in progress; this is not yet a CPU or
complete computer.** Its gate is native logic/storage/loading, reliable tests,
and the real stock Keyboard-to-TTY path, including refocus, pause/reset,
save/reopen, relocation, and offline operation. Mouse/drag findings no longer
block v1. See [acceptance criteria](docs/roadmap.md) and the
[synchronized backlog scope notes](docs/backlog.md).
The [focused M0 evidence report](docs/evidence/m0-keyboard-2026-10-01.md) separates
revised-artifact checks from desktop acceptance still to complete. The
[historical report](docs/evidence/m0-2026-10-01.md) preserves the earlier experiment.

## Open the keyboard terminal bench

The primary `circuits/bitwright.circ` now contains stock Keyboard, TTY, and
gate-built transfer control, with no custom component library. It is a direct
input/output feasibility bench, not the future CPU or boot monitor. Native
fixture libraries remain inspectable in the project tree.

Use the free desktop [Logisim-evolution 5.0.0](https://github.com/logisim-evolution/logisim-evolution/releases/tag/v5.0.0).
Desktop installers include Java. Extract a fresh primary package, open
`circuits/bitwright.circ`, select the Poke tool, enable ticks, and click Keyboard
to type. Use Run=1, Clear=0, Reset=0 for normal input. Run=0 holds queued input;
Clear clears TTY while retaining queued input; Reset clears both. See
[workbench controls](circuits/README.md) for details. Readers need no custom JAR
or compiler. M0 acceptance and a completed release are not yet claimed.

For a source checkout, use Python 3.12+ and JDK 21. Check `python3 --version`
first: `.python-version` does not change the system interpreter by itself. If
`python3` is older than 3.12, select the pinned interpreter with your version
manager or replace `python3` below with its full path. Set `JAVA_HOME` to the JDK
if it is not the default. From the repository root:

```sh
python3 tools/bw.py fetch
python3 tools/bw.py doctor
python3 tools/bw.py test
python3 tools/bw.py run
```

`fetch` downloads and verifies the pinned simulator JAR. Subsequent builds/tests
use the cached JAR; the desktop bench itself needs no network. Linux vector tests
need a display (for example, run `xvfb-run -a python3 tools/bw.py test`). Package
with `python3 tools/bw.py package`; the candidate archive is
`dist/bitwright-m0.zip`. End users of that archive need neither Python nor a compiler.

Build outputs live at the repository root: `build/test-results/`,
`build/roundtrip/`, and `build/renders/`. The default simulator cache is
`.cache/logisim-evolution-5.0.0-all.jar`; `LOGISIM_JAR` can point to an existing
official JAR, which is still checked against the pinned SHA-256.

The preserved mouse/canvas experiment under `experiments/mouse-canvas/` is
available in a source checkout, with its own entry and explicit commands; it is
omitted from the primary ZIP. Older candidate
ZIPs or extracted copies retain their original canvas contents; build/extract a
fresh primary package rather than assuming those copies have changed.

## Approved v1 target

- 8-bit accumulator datapath, 16-bit byte addresses, 32 KiB RAM, and 16 KiB ROM.
- Gate-built ALU, adders, selectors, registers, counters, decoding, and hardwired
  instruction control. Single-bit D flip-flops and bulk RAM/ROM are allowed.
- A manageable [51-instruction ISA](architecture/isa.md), stack/subroutines,
  assembler, boot monitor, and example programs.
- Polling memory-mapped keyboard I/O with circuit-owned buffering and an ASCII
  text monitor through stock TTY.
- A basic command terminal with help, memory dump/edit, and run commands, plus
  arithmetic and memory-test programs.
- Native `.circ` projects that readers can inspect and single-step.

Stock Keyboard and TTY provide host character input and text rendering; the CPU,
device registers, and machine FIFO remain circuit logic. No custom Java bridge
is required by the new v1 target.
Read the [primitive policy](architecture/primitives.md), [memory/I/O contract](architecture/memory-and-io.md),
and [clock/control contract](architecture/control.md) for the exact boundary.

## Build in demonstrable steps

| Milestone | Result |
| --- | --- |
| M0 / `v0.0.1` | Native storage/test/loading and Keyboard-to-TTY feasibility bench |
| M1 / `v0.1` | Verified primitive logic and ALU workbench |
| M2 / `v0.2` | First ROM program executing on the circuit CPU |
| M3 / `v0.3` | Complete ISA, assembler, stack, and loading |
| M4 / `v0.4` | Boot monitor and interactive terminal |
| M5 / former `v0.5` | Deferred optional mouse/graphics extension, outside v1 |
| M6 / `v1.0` | Reproducible offline computer and demonstration release |

The [roadmap](docs/roadmap.md) gives meaningful tests and acceptance evidence for
each stage. M6 depends on M4, with no M5 dependency. The
[milestones](https://github.com/The-CarL/bitwright/milestones) and
[issues](https://github.com/The-CarL/bitwright/issues) now reflect the narrowed
scope; M5 remains open as a deferred optional extension.

## Repository and source ownership

| Location | Contents |
| --- | --- |
| `architecture/` | Approved primitive policy, ISA, memory map, timing, and device target |
| `circuits/` | Manual native sources and deterministic generated `.circ` outputs |
| `tools/` | Circuit generation, testing, auditing, and packaging; later assembler/model |
| `experiments/` | Optional historical mouse/canvas entry, separate from the primary package |
| `bridges/` | Java source used only by the optional mouse/canvas experiment |
| `images/memory/` | Loadable `v2.0 raw` images and manifests |
| `tests/` | Vectors, harnesses, and tool tests |
| `docs/` | Roadmap, evidence, workflow, and build journal |

Manual circuits own their `.circ` source; generator inputs own generated files.
Commit generated outputs with their source and never overwrite manual files from
generation. See [circuit ownership](circuits/README.md), the pinned
[`toolchain.json`](toolchain.json), and [reproducibility policy](docs/workflow.md).
Future `software/` sources arrive with the software milestones.

The [build journal](docs/journal/README.md) follows actual experiments and completed
demonstrations, forming the basis of a future blog series or Forge project.
