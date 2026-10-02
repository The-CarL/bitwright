# From an echo bench to an Apple-1-inspired computer

## Question

The user wanted a minimal programmable computer and a deeper construction story:
assembly files, keyboard input and terminal output, with abstractions built from
gates. The earlier mouse/canvas and custom-ISA direction did not match that goal.

## Design

Target original documented 6502 behavior, a ROM monitor, small RAM and an
Apple-1-style console. Build the CPU's storage from gate latches/flip-flops.
Keep bulk program/character memory and font ROM as declared foundations.
A source-available adapter captures ASCII/file input and displays raw pixels;
circuits own keyboard latching and terminal behavior.

## Experiments and failures

Native CPU tests compare register state and ordered writes with an independent
model, covering all documented encodings. Gate-built state passed capture/hold/
reset tests, but increased simulation time compared with built-in flip-flops.

Independent review found that monitor deposits could overwrite parser workspace
and that a user program could return with decimal mode set, corrupting subsequent
hex parsing. Both received targeted software regression tests and fixes.

The first terminal scanned every character on a full-frame schedule. A circuit-
built immediate-character path now emits eight pixel rows after a write, while
background scanning still handles whole-screen refresh.

An integrated file-loading test exposed practical simulation cost. CPU clock
settings are not throughput measurements. The measured test and any subsequent
optimization belong in the current evidence report before making usability claims.

## Evidence and next uncertainty

The final native integration loaded two different assembly programs through the
ASCII boundary, checked all their bytes in RAM, accepted keyboard input and
returned to the monitor. The sum program computed 45 in circuit RAM. Warm reset
printed a new banner and preserved program memory. The run passed 205 assertions
at 448.8 cycles/s on an Apple M4; small program loads took two to three minutes.
Two native input-to-render samples were 224–240 ms, excluding desktop scheduling.

Gate-only CPU optimizations improved a controlled differential run by 1.67×,
and monitor changes reduced load instruction counts by about 25%. Review also
caught stale-output masking in CI and an original-checkout JAR on the relocation
test classpath; both received fixes before packaging.

See the [implementation evidence](../evidence/apple1-2026-10-01.md), generated CPU
manifest and build/test-results. Historical reports remain unchanged. Desktop
automation repeatedly timed out, so real file-picker/typing, refocus and platform
acceptance remain unverified. Backspace and slow scrolling are documented limits.
The implementing change is tracked in [draft PR #12](https://github.com/The-CarL/bitwright/pull/12);
link its final commit when preparing the published blog.

## Blog outline

1. Define the computer and the host boundary.
2. Build state from gates and discover simulator timing limits.
3. Construct the 6502 datapath and hardwired control.
4. Verify instructions against an independent model.
5. Assemble, transfer and execute a program.
6. Build a text terminal from character storage and pixel logic.
7. Measure, package and explain the finished demonstration and its limits.
