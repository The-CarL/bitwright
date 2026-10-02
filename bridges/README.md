# Bitwright host canvas bridge (M0)

Historical optional mouse experiment. The current computer uses the
[ASCII/raw-pixel console bridge](console/README.md). This canvas JAR is not
included in the default package.

This source-available Java library targets **Logisim-evolution 5.0.0**. It retains a
128 × 128 RGB image and hands host mouse events to circuit pins. It contains no
CPU, instruction logic, address decoding, MMIO, drawing algorithm, or machine-side
FIFO. The machine-side 16-event FIFO belongs to a later circuit milestone.

## Build and tests

Use the project's Python **3.12+** and JDK **21** (the runtime lock records tested patch
version). The official simulator JAR is a compile/test dependency, never bundled
inside the bridge:

```sh
python3 bridges/build.py --logisim-jar /path/to/logisim-evolution-5.0.0-all.jar --jdk-home /path/to/jdk-21
```

The command verifies the simulator manifest, compiles with `--release 21`, runs
plain-Java contract tests against the real simulator API, and writes
`build/bitwright-bridge.jar` at the repository root, not under `bridges/`.
It has no network or external build-tool
dependency. Class order, archive timestamps, permissions, and bytecode debug
metadata are deterministic; repeated builds with the same JDK give the same
SHA-256. Releases include the built JAR; readers do not need the build tools.
The native library class is `org.bitwright.bridge.BitwrightLibrary`; its tool ID
is `BitwrightCanvas`. Both IDs are persistent file-format identifiers.

## Pins and clock contract

The component origin is its upper-left corner, with bounds `(0,0,180,200)`.
The displayed image is `(20,20,128,128)`, one host pixel per simulated pixel at
100% zoom. These offsets are part of the M0 circuit interface.

| Index | Pin | Direction | Width | Offset |
|---:|---|---|---:|---|
| 0 | CLK | in | 1 | (0,20) |
| 1 | RESET | in | 1 | (0,40) |
| 2 | PLOT | in | 1 | (0,60) |
| 3 | CLEAR | in | 1 | (0,80) |
| 4 | X | in | 7 | (0,100) |
| 5 | Y | in | 7 | (0,120) |
| 6 | COLOR | in | 3 | (0,140) |
| 7 | ACK | in | 1 | (0,160) |
| 8 | OV_CLEAR | in | 1 | (0,180) |
| 9 | VALID | out | 1 | (180,20) |
| 10 | MOUSE_X | out | 7 | (180,40) |
| 11 | MOUSE_Y | out | 7 | (180,60) |
| 12 | BUTTONS | out | 3 | (180,80) |
| 13 | OVERFLOW | out | 1 | (180,100) |

All command inputs commit once per **falling CLK edge**; repeated propagation
without an edge has no side effect. ACK high on successive falling edges consumes
one event on each edge, provided VALID was already high on the circuit-facing
output. If a host event arrives at the same propagation step as a falling edge,
it is published first and cannot be consumed before the circuit observes it.
Clear takes priority over plot. A high asynchronous RESET
clears pixels, queue, button state, and overflow and suppresses input while held.
Unknown clock transitions are not edges; unknown plot coordinates/colors cause no
write. The RGB bits are red=4, green=2, blue=1. Pixel and packet coordinates are
0–127. Pixel data is host display state, not RAM accessible to software.

Once VALID is high, the head packet and VALID remain stable until ACK (or RESET),
even if new host events arrive. Empty packet output is zero with VALID=0. Reading pins has no side
effect. Outputs settle with a one-propagation-step delay.

The **host handoff queue holds 256 packets**, separate from the eventual machine
FIFO. Press, drag, and release each enqueue a packet, with no coalescing. Drag and
release coordinates outside the image clamp to its edges. The queue drops the
newest event when full, preserves all retained packet order, and raises sticky
OVERFLOW. OV_CLEAR clears only that flag; it does not restore a dropped transition.
Consumers must reset/resynchronize input after overflow before trusting button
state. Even a release can be dropped when full; that loss is explicit.

## Desktop interaction and limitations

Use Logisim's Poke tool and click inside the black image. Drag produces events;
release clears the released button's bit while preserving other held buttons
(buttons=0 when none remain). When Logisim calls `stopEditing`, the bridge
synthesizes one release if a button was still held. That release remains subject
to the documented queue overflow policy, so it cannot guarantee recovery from a
full queue. The callback does not intercept every OS focus-loss path: the native
desktop smoke test must verify the actual application behavior.
Paused simulation can accumulate host events up to the documented queue limit;
no ACK or pixel command commits until propagation and clock edges resume.

BUTTONS bit0 is primary, bit1 secondary, and bit2 middle. Multiple held buttons
are represented together. The pinned simulator's
[`InstancePokerAdapter`](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/instance/InstancePokerAdapter.java)
first constructs a press without button/modifier metadata, including the event
passed to `init`. Its caller,
[`PokeTool`](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/tools/PokeTool.java),
then forwards the original event. The bridge ignores the synthetic first press
and captures the original, avoiding duplicate packets and preserving button
identity. Automated callback tests cover all button bits; actual desktop button
routing also depends on the platform's context-menu/gesture handling and must be
verified in the native smoke test. No hover events are provided by
[`InstancePoker`](https://github.com/logisim-evolution/logisim-evolution/blob/v5.0.0/src/main/java/com/cburch/logisim/instance/InstancePoker.java).

Host data access is synchronized across the AWT event and simulator threads.
Simulation-state clones copy the image and queue independently, including edge
history; immutable packets can safely be shared. Host image/queue state is
transient and is not serialized into `.circ` files.

The automated tests cover RGB colors and corners; falling-edge/unknown-clock
behavior; clear/reset priorities; stable packets; capacity/overflow/draining;
focus-stop release; independent state cloning; actual library registration,
port locations, widths and callback-to-pin translation; and a host event arriving
at the same propagation step as an acknowledgement edge. They do not substitute
for opening a native project and exercising real mouse events in the desktop app.
