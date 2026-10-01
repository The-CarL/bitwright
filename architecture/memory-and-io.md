# Memory, boot, and device boundaries

Status: approved v1 map and behavior. Device block offsets below are reserved as a
concrete integration target; M0 must prove the host boundary, and later device
milestones must lock bit-level register contracts before firmware depends on them.

## Memory map

| Addresses | Use |
| --- | --- |
| `0000–7FFF` | 32 KiB RAM; stack at `0100–01FF` |
| `8000–80FF` | Memory-mapped I/O |
| `8100–BFFF` | Reserved: reads return `FF`, writes have no effect |
| `C000–FFFF` | 16 KiB ROM |

ROM writes have no effect. RAM is byte-wide and software cannot execute the host
bridge. Reset enters ROM at `C000`; the eventual release embeds its boot/demo ROM.
Warm reset preserves RAM. Cold RAM contents must not be treated as initialized by
software unless supplied by an explicit image.

The boot monitor prints a banner and provides help, memory dump/edit, program
execution, and demo commands. GUI loading occurs while stopped, followed by reset
or a monitor jump into RAM. Automated tests use labelled RAM/ROM images through
Logisim's TTY loading path. Use `v2.0 raw` images with deterministic full-bank
padding and a separate manifest specifying bank origins and entry points.

## Device blocks and reserved offsets

All devices use polling in v1. Input reads are non-destructive; an explicit
acknowledgement pops one complete item. Commands are writes and must commit once.

| Block | Reserved offsets |
| --- | --- |
| `8000–800F` keyboard | `+0` status, `+1` data, `+2` acknowledge, `+3` clear overflow |
| `8010–801F` terminal | `+0` output character, `+1` clear |
| `8020–802F` mouse | `+0` status, `+1` X, `+2` Y, `+3` buttons, `+4` acknowledge, `+5` clear overflow |
| `8030–803F` display | `+0` X, `+1` Y, `+2` color, `+3` plot, `+4` clear |

Unused device addresses remain reserved. The status-bit layout and empty-read
value are intentionally not a firmware ABI yet; record them with FIFO acceptance
tests before M4/M5. No CPU-visible device register or FIFO is implemented in M0.

## Host boundary

**Keyboard:** stock seven-bit ASCII Keyboard feeds a circuit-built 16-byte FIFO
using permitted RAM. Circuit logic owns FIFO pointers, status, and overflow. The
stock host buffer is finite and does not export overflow; report this limitation
separately from the circuit FIFO. Raw key-up/key-down scan codes are outside v1.

**Terminal:** stock TTY renders seven-bit characters and accepts clear. Keep it
visually distinct from the graphics canvas.

**Mouse:** a source-available Java canvas reports absolute 7-bit X/Y coordinates
and button state for press, drag, and release. Clamp coordinates to 0…127. A
circuit-built 16-event FIFO stores complete packets until acknowledgement; packet
fields remain stable while valid. Host and circuit queues have separately reported
capacity and overflow. Preserve accepted button transitions in order. Hover
movement is outside v1. Release outside the canvas, focus loss, pause/resume,
reset, and overflow behavior require evidence from the actual simulator.

**Display:** 128×128 pixels, 3-bit RGB color; circuit registers issue individual
plot/clear commands. The Java canvas retains pixels and captures gestures, but
does no CPU address decoding, drawing algorithm, or CPU-visible FIFO management.
Stock RGB Video is also exercised in M0 as a distinct proven pixel sink.

Use `valid/data/ack/reset` at the live/scripted input boundary. The M0 bridge's
pin-level interface is documented with its source; it is not a memory-mapped
device by itself. Full redraw requires 16,384 pixel commands before CPU overhead;
v1 promises interactivity only after measurement, not animation frame rates.
