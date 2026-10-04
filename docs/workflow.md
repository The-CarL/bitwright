# Build and source-of-truth workflow

Pin Logisim-evolution 5.0.0 and its SHA-256 in toolchain.json; use Python 3.12+
and JDK 21 for development. End users install Logisim and open the complete package.

1. `python3 tools/bw.py fetch` obtains/verifies the simulator.
2. `python3 tools/bw.py build` compiles the console adapter, assembles firmware
   and demos, generates native circuits, and audits the component boundary.
3. `python3 tools/bw.py test` runs software tests, native fixtures, CPU comparison,
   terminal tests, full file-loading/program execution, and native round trips.
4. `python3 tools/bw.py package` builds a deterministic ZIP and checks relocation.
5. `python3 tools/bw.py offline-test` verifies process-local network denial and
   boots the extracted computer without changing host network settings.

Linux vector mode needs a virtual display. Use `xvfb-run -a` for the test command.
Tests parse explicit results and apply watchdogs; Logisim's zero exit status alone
does not prove test-vector success.

## Ownership

Manual .circ sources remain authoritative under circuits/manual. Generated
projects are owned by tools/generate_circuits.py (legacy fixtures),
generate_6502.py (CPU), generate_terminal.py (console), and generate_machine.py
(top-level integration). Software .asm and original font definitions own their
generated images/ROM contents. Commit inputs and generated native outputs;
`check-generated` is read-only. Never edit generated XML as the lasting fix.
CI checks the committed outputs before generation and rejects any tracked build
diff. Relocation checks compile harness sources and load the console JAR from the
extracted package itself, so a checkout dependency cannot hide a missing library.

## Package

The ZIP contains native projects, relative libraries, prebuilt console JAR,
assembly demos/load records, source tools and documentation, including the
illustrated architecture gallery, its PNGs and generation prompts. Gallery links
are relative and work in the extracted package. It excludes the mouse experiment
and its JAR. The simulator itself is installed separately.
Checksums cover every package entry; fixed timestamps/order make repeat builds
comparable. Java compilation targets 21 and strips debug paths.

Upgrades require a dedicated compatibility change with regeneration, native
execution, save/reopen, relocation and desktop tests. Preserve old evidence
as historical reports rather than rewriting it to describe new artifacts.
