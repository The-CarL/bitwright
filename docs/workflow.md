# Source ownership and reproducibility

## Current artifact and amended target

The 2026-10-01 scope amendment makes v1 a keyboard/text-terminal computer through
stock Keyboard and TTY. Mouse, pixel graphics, framebuffer, and custom Java bridge
are outside v1. Existing circuits, bridge code, generators, tests, and packaging
are preserved. In particular, the current entry `circuits/bitwright.circ` and
`dist/bitwright-m0.zip` still contain and depend on the earlier canvas bridge.
Their commands below describe that existing experiment, not an already adapted
keyboard/TTY-only release.

Adapting the entry and package is pending implementation under M0. The amended
release must open using the pinned simulator without a required custom bridge;
keep the optional historical experiment reproducible separately. Do not remove
its code or overwrite its evidence merely because it is outside current scope.

## One owner per artifact

Use a mixed authoring workflow:

- Hand-authored educational leaves and layouts own their `.circ` content.
  Save/reopen them with the pinned simulator; generators must not overwrite them.
- Generator inputs own repetitive bit slices/assemblies and generated memory
  images. Commit those inputs and the native generated `.circ` outputs, with a
  visible generated-file marker and deterministic regeneration check.
- Each circuit must be classified manual or generated; do not silently change its
  owner during a simulator save. Save a temporary copy for generated round trips.
- Native XML parsing is only one check. Load behavior, save/reopen behavior,
  vectors, recursive primitive auditing, and readable visual layout also matter.

Generated and manual equivalent fixtures in M0 are separate files so equivalence
can be demonstrated without making the manual source an accidental output.
The M0 entry project `circuits/bitwright.circ` is generated; only
`circuits/manual/foundations.circ` is manually owned at this stage. The ownership
table in [circuits/README.md](../circuits/README.md) identifies the actual sources.

## Versions and packaging

Pin Logisim-evolution **5.0.0**. The official portable all-in-one JAR's validated
SHA-256 is `6b368e894742c04cc83aa9830f869bcab0190ede4df43ad6fecdb89b3a23a41c`.
The portable runtime and bridge API require Java 21 or newer. Building the bridge
requires JDK **21**, enforced for reproducible bytecode. M0 uses Temurin
`21.0.12.1+1`; the Python minimum is **3.12**, with `3.12.12` tested. The repository
toolchain lock and its verification tooling are authoritative for exact download
assets/checksums. Desktop installers
bundle Java. Revalidate circuits, vectors, stock keyboard/TTY behavior, and any
preserved experimental bridge linkage in a dedicated compatibility change before
updating the simulator pin.

Use relative library references. The existing experimental M0 candidate ZIP contains
native circuits/libraries, a prebuilt bridge JAR with its source, development
tools/tests, memory images, documentation, the toolchain lock, and
`SHA256SUMS.json`. The amended keyboard/TTY package must not require the custom
canvas JAR; that packaging change has not happened yet. Final release packaging
must also include applicable license notices. Readers install the pinned free desktop simulator,
extract the ZIP, open the entry `.circ`, reset, and enable ticks. Readers do not
need Python or a Java compiler; runtime code requires no network access.

The default build directory is `build/` at the repository root, not `bridges/build/`.
The bridge is `build/bitwright-bridge.jar`; test logs and native round-trip copies
go to `build/test-results/` and `build/roundtrip/`. `tools/bw.py package` writes
`dist/bitwright-m0.zip`. It builds/audits and tests relocated native/JAR loading;
it does not replace `tools/bw.py test` or real desktop acceptance.

`python3 tools/bw.py render` compiles the development-only native renderer and
pixel smoke check for the preserved experiment against the pinned simulator. It exercises stock RGB Video
through the circuit's input pins and writes native circuit renders under
`build/renders/`. The full test command also runs these checks. These are rendered
artifacts using Logisim's component painters, not desktop screenshots or evidence
of real mouse routing. These graphics checks remain in the current test command
but are not amended v1 acceptance requirements. The pixel checker reads the stock
display's private image field; simulator upgrades must revalidate this explicitly
pinned adapter while the optional experiment remains supported.

Do not claim a release works offline until it has been extracted into a different
directory and exercised without network access. Do not bundle an unverified
simulator binary or publish an unsupported-platform claim from one-machine tests.

## Artifact organization

| Directory | Saved artifacts |
| --- | --- |
| `architecture/` | Markdown contracts and machine-readable opcode specification |
| `circuits/` | Native `.circ` projects/libraries, with explicit manual/generated ownership |
| `tools/` | Standard-library Python tooling, generator, test runner, future assembler/model |
| `bridges/` | Preserved optional mouse-canvas Java experiment and build configuration |
| `software/` | Future boot/runtime/demo `.asm` sources |
| `images/memory/` | `v2.0 raw` byte images, listings, symbols, bank-origin manifests |
| `tests/` | Text vectors, native harnesses, assembly tests, expected traces |
| `docs/` | Journal, SVG diagrams, screenshots, evidence reports, user/developer guidance |

Add future directories when they have content. Avoid placeholder artifacts that
could be mistaken for a completed subsystem. Memory images are fully padded and
deterministic; origins and entry points belong in an explicit load manifest.

## Review and acceptance

Every issue names an observable demonstration, dependencies, meaningful tests,
and closure evidence. Check acceptance before closing an issue; a merged change
does not by itself prove a desktop integration gate. Keep evidence factual and
identify tests that still require another platform or real host interaction.

M0 acceptance now covers native/test/storage/loading and stock Keyboard-to-TTY
desktop behavior, including refocus, pause/resume, reset, save/reopen, offline
operation, and relocation. Mouse/drag findings are not blockers. M0 remains open;
the v1 release path is M0 through M4, then M6, with M5 deferred outside that chain.

The eventual reference CPU model is test tooling, never a hidden implementation
of the delivered computer. Gate logic remains visible and inspectable in `.circ`.
