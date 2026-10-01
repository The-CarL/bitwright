# Bitwright

**From gates to pixels: building a complete 8-bit computer in Logisim-evolution.**

This project revisits an unfinished computer engineering undergraduate ambition: build a working computer end-to-end from primitive circuit components, with a CPU, memory, keyboard and mouse input, and a monitor.

## Status

Planning stage. No working computer or circuit files have been implemented yet. The exact primitive-component boundary, instruction set, memory capacity, and host input/output integration remain design decisions.

## Goals

- An inspectable 8-bit CPU built from primitive logic.
- Memory and basic keyboard, mouse, and display I/O.
- Readable, hierarchical circuits that can be explored and single-stepped.
- Reproducible builds and meaningful circuit and program tests.
- A build journal to support a future blog series or Forge project.

## Local experience

The intended runtime is the free, open-source desktop application [Logisim-evolution](https://github.com/logisim-evolution/logisim-evolution). The primary hardware artifact will be a native `.circ` project opened in that application. The tested simulator version will be pinned when implementation begins.

Host keyboard, mouse, and display integration must be prototyped before committing to an interface. Any host bridge will be documented separately from the computer's circuit logic.

## Proposed milestones

1. Define allowed primitives and architecture; prototype host I/O.
2. Build and test the ALU and registers.
3. Execute the first program with instruction control and memory.
4. Add keyboard input and text output.
5. Add graphics and mouse interaction.
6. Build a boot environment and demonstration programs.

## Planned artifacts

| Location | Contents |
| --- | --- |
| `circuits/` | Complete computer and reusable native circuit libraries |
| `architecture/` | Primitive policy, instruction set, memory map, and device interfaces |
| `tools/` | Assembler and any circuit-generation tooling |
| `software/` | Boot software and example assembly programs |
| `images/memory/` | Loadable program, font, and other memory images |
| `tests/` | Circuit vectors and CPU/system test programs |
| `docs/` | Diagrams, screenshots, and build journal |

These directories will be added as their contents are implemented. If circuits are generated, both source tooling and generated `.circ` files will be committed, with an explicit policy for manual edits.

## Background

The project began with the excitement of building complex circuits in Logisim during undergraduate study, and the desire to finally turn those pieces into a complete interactive computer.
