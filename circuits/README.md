# Native circuit projects

Open `bitwright.circ` in Logisim-evolution 5.0.0 with the complete package folders.
It depends on generated CPU/terminal libraries and build/bitwright-console.jar.
Reset starts at 1 to initialize gate feedback. Set Reset to 0, enable ticks,
enter Apple1Console, and use the Poke tool on the screen. Wait for the firmware
prompt before choosing a .mon file.

The CPU instance exposes registers, instruction/state and bus signals. Enter
Cpu6502 to inspect InstructionDecode, Alu6502, register banks, FullAdder, GateDff
and GateLatch. The CPU file contains no built-in Memory-library components.
The console's ConsoleLogic contains its MMIO and terminal circuits. Character RAM,
glyph ROM and individual console D flip-flops remain explicit foundations.

| File | Owner and purpose |
| --- | --- |
| bitwright.circ | tools/generate_machine.py; CPU, console, memory and gate decoding |
| generated/cpu6502.circ | tools/generate_6502.py; gate-only CPU and educational state/arithmetic leaves |
| generated/cpu6502-manifest.json | Generated coverage, counts, timing and fidelity limits |
| generated/terminal.circ | tools/generate_terminal.py; keyboard and circuit-built text display |
| manual/foundations.circ | Authoritative manually saved gate/load-bit fixture |
| generated/foundations.circ | Generated equivalent fixture |
| terminal-bench.circ | Historical Keyboard-to-TTY test fixture, no CPU |
| generated/ram-harness.circ | Bounded native RAM loading/signature test |
| generated/never-halt.circ | Deliberate watchdog failure fixture |

The historical terminal bench has Run, Clear and Reset controls: Run forwards
queued stock keyboard characters, Clear clears TTY while holding queued input,
and Reset clears both. It remains useful for simulator regressions but does not
represent the current machine.

Generated files are committed inspectable outputs. Edit their named generators,
then run build and check-generated. Never regenerate over manual files. Reset
and behavioral native tests are required after save/reopen, not XML parsing alone.
