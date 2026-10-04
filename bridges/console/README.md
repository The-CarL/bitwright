# ASCII and raw-pixel host adapter

This is a small Logisim-evolution **5.0.0 / Java 21** library. `ConsoleHost` captures ASCII, queues input from a `.mon` text file, and retains a 320 × 192 monochrome pixel image. It contains **no CPU, instruction interpreter, address decoder, character font, cursor, terminal wrapping, or scrolling**.

The native `circuits/generated/terminal.circ` owns those terminal operations. Its inspectable `ConsoleLogic` uses gates, wiring, individual D flip-flops, 2,048 × 7-bit character RAM (24 rows used with a 64-character stride), and a 1 KiB font ROM. `ConsoleMux*`, `ConsoleAdd*`, and `ConsoleRegister*` are native gate subcircuits. The original 5 × 7 glyph drawings and generator are authoritative in `tools/generate_terminal.py`; generated `.circ` files are committed outputs, not manually edited sources.

## Build and verify

```sh
python3 bridges/console/build.py --logisim-jar "$LOGISIM_JAR" --jdk-home "$JAVA_HOME"
python3 tools/generate_terminal.py
mkdir -p build/terminal-tests
"$JAVA_HOME/bin/javac" --release 21 \
  -cp "$LOGISIM_JAR:build/bitwright-console.jar" \
  -d build/terminal-tests tools/java/TerminalSmoke.java
"$JAVA_HOME/bin/java" -Djava.awt.headless=true \
  -cp "$LOGISIM_JAR:build/bitwright-console.jar:build/terminal-tests" \
  TerminalSmoke circuits/generated/terminal.circ
```

Use `;` rather than `:` as the Java classpath separator on Windows. The builder checks the simulator version, compiles without network access, tests the host state, and writes a deterministic JAR at `build/bitwright-console.jar`. The native test drives the real Logisim circuit and checks keyboard acknowledgement, character RAM and font pixels, wrapping, scrolling, clear, and reset. It does not reimplement terminal logic in Java.

## Visible use

Right-click the `Apple1Console` instance in the main computer and choose **View Apple1Console**. Opening the library definition instead shows an independent circuit state. Choose the Poke tool and click the pixel screen to type. The **Load ASCII .mon file** button queues a monitor-input text file. Start/reset the computer and wait for its monitor prompt **before** selecting a file; reset clears pending host input.

The loader validates ASCII and normalizes CRLF/LF to a single CR. It does not parse hexadecimal addresses or instructions and does not access RAM. Gate-built keyboard hardware delivers one character at a time; firmware running on the circuit CPU interprets monitor commands and deposits program bytes.

The host queue holds at most 65,536 characters, including interactive input and selected files. An oversized/invalid file is rejected atomically. Interactive overflow sets a visible flag and drops newly arriving characters. Reset clears the queue and flag. This host queue is deliberately separate from the **one-character circuit-built keyboard latch**.

## Machine bus contract

The console accepts `Address[16]`, `DataIn[8]`, `Write`, `Read`, `SysClock`, and `Reset`; it returns `DataOut[8]`, `Ready`, and `Busy`. Cursor column, cursor row, and scroll origin are debug outputs. `Read` must identify actual bus reads, not merely the absence of a write.

| Address | Read | Write |
| --- | --- | --- |
| `D010` | Last latched ASCII in bits 0–6, bit 7 = ready; a rising-edge read acknowledges the latch | Ignored |
| `D011` | Bit 7 = keyboard ready; other bits zero | Accepted and ignored |
| `D012` | Bit 7 = terminal busy; other bits zero | On a falling edge while ready, accepts bits 0–6 as an ASCII character |
| `D013` | Zero | Accepted and ignored |
| Other | Zero | Ignored |

This is a **monitor-oriented PIA register subset**, not a complete MOS 6820 emulation. In particular, DDR selection, interrupt flags, and hardware interrupt outputs are absent. Software must poll status and write only when the display reports ready.

The CPU captures `D010` data on the rising edge. That same edge clears ready. While the latch is empty, a later rising edge captures the advertised host byte and acknowledges the host queue. The host never advances merely because simulation is running: it requires an explicit circuit acknowledgement.

`Reset` asynchronously clears circuit state and character RAM and clears the host queue/image. The terminal supports printable ASCII, CR/LF newline, backspace within the current line, and form feed. Form feed commits on a falling edge and reports busy for one subsequent cycle. Backspace moves the cursor left without erasing; the next printable character replaces that cell. The display shows uppercase glyphs for lowercase letters. It has no ANSI escape-sequence interpreter.

## Pixel boundary and scanning

`ConsoleHost` receives a six-bit word column (0–39), an eight-bit pixel row (0–191), an eight-bit bitmap, and draw enable. On a falling edge, it copies those eight bits to eight adjacent pixels; bit 0 is the leftmost pixel. Expanding a raw pixel word is its only rendering operation.

An accepted printable character is latched with its cursor coordinates and immediately rendered in **eight cycles**, using a circuit-built three-bit glyph-row counter and the font ROM. Busy remains asserted during these eight pixel-word writes, so ordinary typing does not wait for a full screen scan.

The circuit also increments background scan counters, selects character RAM, reads font ROM, and emits pixel words. A full background scan takes **7,680 cycles**, with character rendering/writes/scroll clearing able to suppress individual background transfers until a later scan. Scrolling visibility therefore still depends on the scan rate. This implementation does not claim the original Apple-1 video timing, analog composite output, or frame rate. CPU execution and pixel scanning currently share the clock. Measurements and possible independent scan-clock work belong in the performance milestone.

Scrolling is performed by a circuit-built circular row origin. A newline below the last visible line advances this origin modulo 24 and clears the new bottom row through forty RAM write cycles. The host sees only the resulting pixels and never moves text or pixels on its own.

## Source references

The component API and RAM/ROM pin placement were checked against the pinned official source:

- [InstanceFactory](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/instance/InstanceFactory.java)
- [InstancePoker](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/instance/InstancePoker.java)
- [RAM appearance and ports](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/std/memory/RamAppearance.java)
- [ROM contents serialization](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/std/memory/Rom.java)
