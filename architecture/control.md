# Clock, reset and control

Hardwired gates decode instructions and advance a multicycle state machine. The CPU generator defines transitions/enables; native subcircuits expose them. No control ROM.

CPU registers advance on rising edges. Settled RAM/display writes commit on falling edges. Keyboard read side effects occur on the rising edge when the CPU captures the byte; consuming on the preceding falling edge would change the data too early. Explicit Read suppresses acknowledgement during internal cycles.

Reset suppresses writes and takes priority over faults. The reset sequence reads FFFC/FFFD. Firmware initializes workspace/stack; warm reset preserves RAM. Unsupported instructions visibly fault. Pausing clocks stops instruction execution.

Expose PC, A/X/Y/SP/P, opcode, state, address, data, Read, Write, Sync and Fault. Sync identifies fetch, not automatically retirement. Tests must sample the implemented phases and compare ordered transactions. Every harness needs a watchdog and an explicit result. No cycle-perfect NMOS bus timing is claimed.
