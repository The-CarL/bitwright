# Memory, boot, and device boundaries

Status: approved v1 target, amended on **2026-10-01** to keyboard and a text
monitor/basic terminal. CPU, ISA, RAM/ROM capacity, and boot address remain
unchanged. M0 must prove the stock Keyboard-to-TTY path; no mouse, pixel display,
framebuffer, or custom Java bridge is required by v1.

## Memory map

| Addresses | Use |
| --- | --- |
| `0000–7FFF` | 32 KiB RAM; stack at `0100–01FF` |
| `8000–800F` | Keyboard memory-mapped I/O |
| `8010–801F` | Terminal memory-mapped I/O |
| `8020–80FF` | Reserved: reads return `FF`, writes have no effect |
| `8100–BFFF` | Reserved: reads return `FF`, writes have no effect |
| `C000–FFFF` | 16 KiB ROM |

The former mouse/display blocks `8020–803F` are now reserved with the same
`FF`-read/ignored-write behavior. No device or framebuffer occupies them in v1.
These are target decoding semantics; M0 has no CPU memory map yet.

ROM writes have no effect. Reset enters ROM at `C000`; the eventual release
embeds the boot/monitor ROM. Warm reset preserves RAM. Software must not rely on
cold RAM contents unless supplied by an explicit image.

The basic terminal monitor prints a boot banner and provides help, memory
dump/edit, and program run commands. Arithmetic and memory-test programs supply
the v1 demonstrations.

The monitor's run command places the requested entry address in X and uses
`CALL run_trampoline`; the trampoline executes `JMP X`. A user program returns
with `RET`, consuming the return address that CALL placed on the stack and
resuming the monitor. User programs must balance their stack operations. The
monitor's fixed scratch-memory allocation and permitted load range remain future
firmware decisions; settle them before implementing the monitor. No CPU or
monitor firmware exists in M0.

GUI memory loading occurs while stopped, followed by reset or the monitor's run
command. Automated tests use labelled RAM/ROM images through Logisim's TTY loading
path. Use `v2.0 raw` images with deterministic full-bank padding and a separate
manifest specifying bank origins and entry points.

## Device blocks and reserved offsets

Devices use polling. Keyboard reads are non-destructive; an explicit
acknowledgement pops one character. Commands are writes and must commit once.

| Block | Reserved offsets |
| --- | --- |
| `8000–800F` keyboard | `+0` status, `+1` data, `+2` acknowledge, `+3` clear overflow |
| `8010–801F` terminal | `+0` output character, `+1` clear |

Unused device addresses remain reserved. Status-bit layout and the empty keyboard
read value are not a firmware ABI yet; lock them with FIFO acceptance tests before
M4 firmware depends on them. No CPU-visible device registers or FIFO exist in M0.

## Host boundary

**Keyboard:** stock seven-bit ASCII Keyboard will feed a circuit-built 16-byte
FIFO using permitted RAM. Circuit logic owns FIFO pointers, status, overflow,
and acknowledgement. Dequeue the stock Keyboard only when its head character is
actually accepted into the circuit FIFO. A full FIFO applies backpressure; it
must not consume and discard a character. Test that filling the FIFO, holding it
full, and then draining it preserves the accepted character order. The stock host
buffer is finite and does not export overflow; backpressure does not remove that
separate host-buffer limitation. Raw scan codes and key-up/key-down input are
outside v1.

**Text monitor:** stock TTY renders seven-bit characters and accepts clear.
It is the v1 monitor; there is no pixel-video or framebuffer subsystem. Keep
host rendering distinct from the circuit device registers and terminal software.

Use a documented valid/data/ack/reset boundary between the keyboard adapter and
circuit logic so scripted inputs can exercise the same interface. M0 desktop
acceptance includes typing, keyboard refocusing, pause/resume, reset,
save/reopen, relocation, and network-disabled operation. Initial visible text
entry is proven, but M0 remains open pending the remaining checks.

## Preserved earlier experiment

The earlier stock RGB Video and custom mouse canvas now have a separate entry at
`experiments/mouse-canvas/workbench.circ`. Their implementation and historical
measurements are retained, with explicit experiment tooling. The primary
`circuits/bitwright.circ` contains only the focused Keyboard/TTY bench and native
logic/storage foundations. Older ZIPs retain their original contents. Mouse/drag
limitations remain optional-extension findings, not v1 blockers.
