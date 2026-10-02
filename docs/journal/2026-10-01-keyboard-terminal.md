# 2026-10-01 — Focus the bench on keyboard and text

## Question

Can the first feasibility milestone exercise native circuits, storage/loading,
and a reliable stock Keyboard-to-TTY desktop path with no custom runtime bridge?

## Work in progress

The approved v1 target remains an 8-bit datapath, 16-bit addresses, 32 KiB RAM,
16 KiB ROM, and the 51-instruction ISA. The new implementation separates a focused
primary entry and package from the preserved optional mouse/canvas experiment.
No CPU, assembler, boot monitor, or machine-side FIFO has been implemented.

For the future FIFO, stock Keyboard must dequeue only when the circuit actually
accepts a character; full applies backpressure instead of dropping its head.
For the future monitor, CALL enters a trampoline that uses JMP X to run the user
program, whose RET returns to the monitor. The monitor's scratch memory and allowed
load range are still decisions for the firmware milestone.

## Evidence and next uncertainty

The focused entry and separate experiment tooling are implemented. All sixteen
TerminalControl truth-table rows and eight workbench reset/control rows passed;
the main and control layouts were rendered and visually inspected. These results
do not establish the desktop or offline gate.

The default suite then passed fifteen Python tests and eighteen native keyboard/TTY
assertions, along with both foundation-vector sets, deliberate failures, RAM
signatures, headless terminal echo, and native save/reopen. Clear and Reset now
have distinct tested effects: Clear holds queued characters while clearing TTY;
Reset clears both. The configured 32-character stock host queue silently discards
the 33rd character when full. This measured host limitation remains separate from
the future machine FIFO's backpressure contract.

The focused package then passed manifest/checksum and ZIP-integrity checks,
fresh-path native loading, RAM signature, and exact terminal echo. Reversing input
enumeration with an unchanged source snapshot produced identical archive bytes.
The same RAM and text paths passed with macOS per-process networking denied,
after a live loopback control confirmed the restriction. This proves that
command-line path under isolation; it does not substitute for desktop testing.

Extending native save/reopen coverage from the foundations to the primary bench
then found a format-level failure: after serialization reordered components,
tunnel label `Clock` collided with the built-in Clock component, producing a
modal warning and hanging vector execution. Renaming the primary tunnel to
`SysClock` fixed it: the saved project passed recursive library audit, sixteen
control and eight workbench vectors, and exact Keyboard-to-TTY echo. The native
serializer rebased the foundation library path correctly. The earlier package
was then rebuilt with that fix, and package validation plus the macOS
network-denied RAM/echo tests passed again. Archive checksums must still be
regenerated after documentation changes; no fixed release hash is claimed here.

The focused implementation is recorded in
[commit b41aa8c](https://github.com/The-CarL/bitwright/commit/b41aa8c686a5019dba54bcc71c2507213031dfa8).
[Linux CI run 36884557736](https://github.com/The-CarL/bitwright/actions/runs/36884557736)
passed the full native suite and produced package bytes identical to the macOS
snapshot. Its elevated offline step selected Java 17 rather than the required
Java 21 and failed on class-version compatibility. Explicit runtime-environment
forwarding is being corrected and awaits CI verification; the run is not green.

The [focused M0 evidence ledger](../evidence/m0-keyboard-2026-10-01.md) records
the remaining revised-artifact tests and desktop checks as they become available.
The [earlier journal](2026-10-01.md) and evidence retain the historical experiment.
Neither previous mouse tests nor native renders prove the focused desktop gate.

One preparation check in the still-open old bench accepted `TEST` and Return
after refocusing stock Keyboard, visibly appending the text. The earlier
automation-only refocus failure was not reproduced in that attempt; its cause
remains unknown. Fresh-entry typing, deliberate focus changes, controls,
save/reopen, relocation, and enforced offline operation still need evidence.

Fresh-primary desktop validation then stalled on attachment/accessibility errors:
the original Logisim `getAXState` timed out with `-10005`, native Open-dialog input
did not change, and a Finder launch could not be verified. A network-denied test
process launched, but automation could not attach to its GUI. The original unsaved
historical window was preserved. The earlier `TEST` success belongs only to that
old bench; the new entry has no verified desktop or offline-GUI result. Verified
headless network-denied tests remain a separate result.

M0 remains in progress. No completed release or CPU expansion is claimed.
