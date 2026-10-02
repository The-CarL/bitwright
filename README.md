# Bitwright

**An Apple-1-inspired computer built from inspectable gates in Logisim-evolution.**

Bitwright revisits an unfinished computer-engineering undergraduate ambition:
build a computer from the ground up, then write assembly programs and watch them
execute. The approved target is original NMOS 6502 instruction behavior, ASCII
keyboard input and a circuit-built text terminal. Mouse input is outside this
target.

## What is implemented

The primary native project connects a gate-built 6502 core, 4 KiB RAM, firmware
ROM, a keyboard interface and a 40x24 terminal. The CPU's storage is built from
gate latches and flip-flops; it contains no built-in memory components. Native
subcircuits expose the ALU, decoder, registers, arithmetic and control. The
console uses disclosed single-bit D flip-flops, character RAM and glyph ROM.

An original boot monitor reads characters, deposits/examines RAM and starts
programs. Assembly tools produce machine bytes and `.mon` files. The host file
feeder only supplies ASCII; firmware running on the circuit CPU loads RAM.
The host display only retains circuit-generated pixel words. Cursor, font lookup,
wrapping, scrolling and pixel generation are circuits.

This is a development candidate, not a cycle-perfect Apple-1 replica. The
[architecture](architecture/apple1-direction.md) and
[CPU manifest](circuits/generated/cpu6502-manifest.json) define the fidelity
boundary. The [roadmap](docs/roadmap.md) separates implementation from release
acceptance. Earlier M0 reports and the old echo bench remain historical fixtures.

## Open and run

Use **Logisim-evolution 5.0.0**. Extract the complete `bitwright-apple1.zip` package
and keep its folders together; it includes the prebuilt console JAR. Open
`circuits/bitwright.circ`.

1. Select the Poke tool. **Reset starts at 1** to initialize gate storage; set it to 0.
2. Enable automatic ticks in the Simulation menu.
3. Right-click the **Apple1Console instance on the main circuit** and choose
   **View Apple1Console**. This enters the running instance; opening its library
   definition would show separate, unconnected state.
4. Wait for the `BITWRIGHT` banner and backslash prompt.
5. Click **Load ASCII .mon file** and select `images/memory/6502-sum.mon`.
6. The monitor loads the program and runs it. When prompted, type `9`.
   It computes `SUM (HEX) = 2D` (45 decimal), then returns to the monitor.

Try `6502-hello.mon` and `6502-memory.mon` without changing the circuit. Program
files include a run command. Reset clears queued input and the display but
preserves program RAM. Wait for the prompt before loading a file.

Monitor commands accept either case. Backspace removes a buffered character but
only moves the visible cursor left within the current row; it does not erase the
old glyph or cross a wrapped row. Escape abandons the current command.

The clock setting requests 65,536 ticks/s; actual speed depends on the simulator
and machine. Do not interpret this setting as a measured CPU frequency.
On the reference Apple M4, the native full-machine test measured **449 cycles/s**;
loading `hello` took **2 minutes** and `sum` took **3 minutes**. The visible queue
can therefore remain busy for a while. Native key-to-render timing was about
224–240 ms; desktop event/repaint latency is still unverified.
See the [implementation evidence and limitations](docs/evidence/apple1-2026-10-01.md).
See [console controls and limitations](bridges/console/README.md).
End users need neither Python nor a compiler. The simulator and package run offline.

## Build from source

Development requires Python 3.12+ and JDK 21. Select them explicitly if your
system defaults differ; set `JAVA_HOME` to the JDK. From this checkout:

```sh
python3 tools/bw.py fetch
python3 tools/bw.py build
python3 tools/bw.py test
python3 tools/bw.py run
```

`fetch` verifies the pinned simulator checksum. `LOGISIM_JAR` can select an
existing official JAR, which is checked against the same checksum. Subsequent
build/test/run commands need no network. Linux vector tests require a display,
for example `xvfb-run -a python3 tools/bw.py test`.

To write your own program, copy a demo and assemble it:

```sh
python3 tools/asm6502.py software/demos/sum.asm --output build/my-sum --entry start
```

Load `build/my-sum.mon` through the console. The assembler also writes a binary,
Logisim image, listing, symbols and an address/checksum manifest. Demo programs
start at `0300` and return using `JMP $FF03`; the monitor source documents its ABI.

`python3 tools/bw.py package` creates `dist/bitwright-apple1.zip` and tests
relocation. `offline-test` verifies per-process network denial and boots the
extracted computer. `check-generated` detects stale artifacts.
`run-bench` opens the earlier Keyboard-to-TTY fixture.

## Repository and source ownership

| Location | Authoritative content |
| --- | --- |
| `architecture/` | Primitive, ISA, memory, timing and host-boundary contracts |
| `circuits/manual/` | Manually saved native educational fixtures |
| `tools/generate_*.py` | Deterministic generated-circuit source |
| `circuits/generated/` | Committed inspectable native generated circuits |
| `circuits/bitwright.circ` | Generated complete machine entry |
| `bridges/console/` | ASCII capture/file feeding and raw pixel presentation |
| `software/` | Original monitor and assembly demonstrations |
| `images/memory/` | Generated images, listings, symbols and load records |
| `tests/`, `tools/java/` | Software and actual native-simulator verification |
| `docs/` | Decisions, evidence, journal, roadmap and instructions |

The reference CPU is a test oracle, never part of the delivered computer.
Generators never overwrite manual circuits. Commit generated artifacts with their
sources and verify regeneration. The optional mouse experiment remains isolated
under `experiments/` and is excluded from the default package.

This is intended as a reproducible demonstration of building abstractions from
gates. Claims should be backed by native artifacts, tests and measured evidence,
not by screenshots alone.
