# Data path, clock, and reset

Status: approved architectural contract. A complete cycle-by-cycle control table
must be reviewed with the M2 controller before its gates are authored; no working
controller is claimed by this document.

## Data path

Use reusable one-bit ALU slices, ripple-carry addition/subtraction, Boolean
operations, and single-bit shifts. Build selection trees from gates. Keep memory
`data_in` and `data_out` separate, and gate selection rather than relying on
multiple drivers of a shared bus. Register enables, counters, flags, and address
decoders are built from the permitted foundations.

The hardwired multicycle controller has explicit fetch, operand, execute, and
commit states. Its readable control table is authoritative for state transitions,
bus ownership, register enables, writes, and instruction retirement. It must not
encode control in ROM. Internal states may be added when the gate-level timing
requires them without changing the software-visible ISA.

## Edge contract

1. CPU state/registers advance on rising clock edges.
2. Memory and device writes commit on falling edges, after address/data/control
   signals have settled.
3. Each requested transaction commits exactly once. A held instruction or state
   must not produce duplicate writes or acknowledgements.
4. Halt/fault disables advancement and all writes. Reset takes priority over halt
   and pending transactions.

Use one clock domain. Test wrappers expose an ordinary clock input pin, so vectors
can express setup, low, and high explicitly. Native Clock components belong in
the interactive/system harness, not in a vector-controlled leaf wrapper.

On reset, set `PC=C000`, `SP=FF`, and clear other CPU/control/device state. Warm
reset preserves RAM; boot software initializes every RAM location it relies on.
Expose microstep, PC, opcode, instruction-retirement pulse, halt, and fault for
single-stepping and automated observation. The controller needs a visible saved
instruction address for diagnosing an invalid opcode.

## Test observations

A system harness exposes an output named exactly `halt`, a separate pass/signature
output, a retirement counter, and a watchdog. Halt alone is never success. Compare
ordered write events and retirement state against an independent model. Include
reset during a pending store, sustained halt, PC rollover, and memory/device
write pulses in the acceptance suite.

Record cycles/second and retired instructions/second separately. The interactive
target is under 250 ms input-to-visible response on a named reference machine;
this remains a measurement goal, not a simulator performance guarantee.
