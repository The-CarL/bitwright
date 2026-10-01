# Bitwright

**From gates to pixels: building an inspectable 8-bit computer in Logisim-evolution.**

This personal project revisits an unfinished computer engineering undergraduate
ambition: build a complete computer from primitive circuits, with a CPU, memory,
keyboard, mouse, terminal, and pixel display.

## Current status

The v1 architecture is approved. **M0, the feasibility bench, is in progress; this
is not yet a CPU or complete computer.** Native logic/storage fixtures, testing
tools, stock I/O, and a source-available mouse canvas establish the first gate.
M0 is complete only when actual desktop artifacts, reliable test failures, and
real mouse/display integration are demonstrated. See [acceptance criteria](docs/roadmap.md)
and [GitHub backlog](docs/backlog.md) for progress and dependencies.
The [M0 evidence report](docs/evidence/m0-2026-10-01.md) separates passing automated
checks from desktop acceptance still to complete.

## Open the bench

Use the free desktop [Logisim-evolution 5.0.0](https://github.com/logisim-evolution/logisim-evolution/releases/tag/v5.0.0).
Desktop installers include Java. A packaged bench includes its prebuilt Java
bridge; extract the entire archive, open `circuits/bitwright.circ`, select the Poke
tool, reset simulation, and enable ticks. Keep the relative folders together.
[Workbench controls](circuits/README.md) explain keyboard, stock pixels, mouse
painting, packet retention, and reset. A release is not claimed until its
acceptance evidence is complete.

For a source checkout, use Python 3.12+ and JDK 21. Check `python3 --version`
first: `.python-version` does not change the system interpreter by itself. If
`python3` is older than 3.12, select the pinned interpreter with your version
manager or replace `python3` below with its full path. Set `JAVA_HOME` to the JDK
if it is not the default. From the repository root:

```sh
python3 tools/bw.py fetch
python3 tools/bw.py doctor
python3 tools/bw.py bridge
python3 tools/bw.py test
python3 tools/bw.py run
```

`fetch` downloads and verifies the pinned simulator JAR. Subsequent builds/tests
use the cached JAR; the desktop bench itself needs no network. Linux vector tests
need a display (for example, run `xvfb-run -a python3 tools/bw.py test`). Package
with `python3 tools/bw.py package`; the candidate archive is
`dist/bitwright-m0.zip`. End users of that archive need neither Python nor a compiler.

Build outputs live at the repository root: `build/bitwright-bridge.jar`,
`build/test-results/`, `build/roundtrip/`, and `build/renders/`. The default simulator cache is
`.cache/logisim-evolution-5.0.0-all.jar`; `LOGISIM_JAR` can point to an existing
official JAR, which is still checked against the pinned SHA-256.

## Approved v1 target

- 8-bit accumulator datapath, 16-bit byte addresses, 32 KiB RAM, and 16 KiB ROM.
- Gate-built ALU, adders, selectors, registers, counters, decoding, and hardwired
  instruction control. Single-bit D flip-flops and bulk RAM/ROM are allowed.
- A manageable [51-instruction ISA](architecture/isa.md), stack/subroutines,
  assembler, boot monitor, and example programs.
- Polling memory-mapped I/O with circuit-owned buffering, an ASCII terminal,
  and a mouse-operated 128×128 three-bit RGB canvas.
- Native `.circ` projects that readers can inspect and single-step.

The host bridge captures events and retains pixels; it does not execute the CPU,
decode addresses, implement machine FIFOs, or run drawing algorithms.
Read the [primitive policy](architecture/primitives.md), [memory/I/O contract](architecture/memory-and-io.md),
and [clock/control contract](architecture/control.md) for the exact boundary.

## Build in demonstrable steps

| Milestone | Result |
| --- | --- |
| M0 / `v0.0.1` | Native I/O-and-test feasibility bench |
| M1 / `v0.1` | Verified primitive logic and ALU workbench |
| M2 / `v0.2` | First ROM program executing on the circuit CPU |
| M3 / `v0.3` | Complete ISA, assembler, stack, and loading |
| M4 / `v0.4` | Boot monitor and interactive terminal |
| M5 / `v0.5` | Mouse-driven painting software |
| M6 / `v1.0` | Reproducible offline computer and demonstration release |

The [roadmap](docs/roadmap.md) gives meaningful tests and acceptance evidence for
each stage. [Milestones](https://github.com/The-CarL/bitwright/milestones) and
[issues](https://github.com/The-CarL/bitwright/issues) track implementation.

## Repository and source ownership

| Location | Contents |
| --- | --- |
| `architecture/` | Approved primitive policy, ISA, memory map, timing, and device target |
| `circuits/` | Manual native sources and deterministic generated `.circ` outputs |
| `tools/` | Circuit generation, testing, auditing, and packaging; later assembler/model |
| `bridges/` | Java host canvas source, contract, and build tests |
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
