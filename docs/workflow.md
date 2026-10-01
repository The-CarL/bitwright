# Source ownership and reproducibility

## Primary bench and optional experiment

The primary entry `circuits/bitwright.circ` is the stock Keyboard-to-TTY bench.
Its Run/Clear/Reset control is gate-built and it loads the native foundation
library. No custom component JAR is required. CPU, monitor firmware, and the
machine keyboard FIFO remain later milestones; M0 acceptance is still open.

The earlier canvas is preserved at `experiments/mouse-canvas/workbench.circ`,
with its Java source in `bridges/`. It has explicit experiment commands and is
excluded from the primary package. Historical evidence retains its original
observations. Older downloaded ZIPs and extracted copies do not change when the
repository's entry is updated.

## One owner per artifact

- Manually authored educational leaves own their `.circ` content. Save/reopen
  them with the pinned simulator; generators must not overwrite them.
- Generator inputs own generated circuits and memory images. Commit inputs with
  their native output and check deterministic regeneration.
- Save disposable copies for simulator round-trip checks. Do not replace a
  generator-owned file with a simulator rewrite.
- XML parsing alone is insufficient: native load/save/reopen, behavioral tests,
  recursive primitive auditing, and readable layouts matter.

The primary entry and `circuits/generated/*.circ` are generator-owned.
`circuits/manual/foundations.circ` is manually owned. The optional canvas is also
generated, using `tools/generate_circuits.py --experiment`; default generation
does not include it. See the [circuit ownership guide](../circuits/README.md).

## Versions and development commands

Pin Logisim-evolution **5.0.0**, with standalone JAR SHA-256
`6b368e894742c04cc83aa9830f869bcab0190ede4df43ad6fecdb89b3a23a41c`.
Development uses Python **3.12+** and JDK **21**; the tested versions in the lock
are Python 3.12.12 and Temurin 21.0.12.1+1. Check the selected interpreter:
`.python-version` does not change system Python by itself. Desktop installers
bundle Java; readers need neither Python nor a compiler.

From the repository root, `python3 tools/bw.py fetch` downloads and verifies the
simulator; `doctor` checks the selected tools. The default `test`, `render`,
`audit`, `run`, and `package` commands target the primary terminal bench and
do not build or require the optional bridge. Linux vector execution initializes
Swing, so use `xvfb-run -a python3 tools/bw.py test`.

Default rendering/tests compile development-only `RenderCircuit` and
`M0TextSmoke` adapters against the pinned simulator. They are test tooling, not
runtime components. Native painter images are artifacts, not desktop screenshots.
Revalidate these version-specific adapters, circuit behavior, and stock
Keyboard/TTY integration in a dedicated simulator-upgrade change.

A full source checkout also offers explicit `bridge`, `test-experiment`,
`audit-experiment`, and `run-experiment` commands for the historical canvas.
Build its bridge before `run-experiment`; `test-experiment` builds it itself.
These commands are not primary-v1 prerequisites and are unavailable from the
focused package because their optional sources are excluded.

## Packaging and offline evidence

`python3 tools/bw.py package` writes `dist/bitwright-m0.zip`, rooted at
`bitwright-m0/`. An explicit source allowlist includes primary native circuits,
memory images, architecture/docs, Python tooling/tests, and development text/render
adapter source. It excludes `bridges/`, `experiments/`, custom JARs, and the
pixel-test adapter. `SHA256SUMS.json` covers the archive's files.

Packaging checks deterministic bytes, ZIP integrity and manifest coverage, then
extracts into a fresh path for native audit, RAM loading, and terminal echo.
It does not replace the full test suite or desktop acceptance. Rebuild the archive
after source/documentation changes so its manifest describes the current candidate.

After packaging, `python3 tools/bw.py offline-test` checks an extracted candidate
with per-process network denial: macOS `sandbox-exec` or a Linux network namespace
when available. A reachable local-socket negative control checks enforcement before
RAM and terminal tests run under the same restriction. Unsupported or denied
isolation fails without claiming an offline pass. This command does not change
the host's global network settings, and its command-line result does not by itself
prove desktop focus, save/reopen, or GUI behavior under isolation.

Readers install the pinned free desktop simulator, extract the whole primary ZIP,
open `circuits/bitwright.circ`, and use the documented controls. The runtime has
no required custom bridge. Final releases must include applicable license notices.
A release is not complete until the fresh-folder offline desktop path is verified.

Build outputs stay at repository-root `build/`: test logs in `test-results/`,
native round trips in `roundtrip/`, and primary renders in `renders/`.
The optional bridge remains `build/bitwright-bridge.jar`; experiment renders use
`build/experiment-renders/`. Do not commit caches or compiled artifacts.

## Acceptance and later artifacts

M0 covers native/test/storage/loading and stock Keyboard-to-TTY desktop behavior:
refocus, pause/resume, reset, save/reopen, offline operation, and relocation.
Track actual results in the [focused report](evidence/m0-keyboard-2026-10-01.md).
Mouse/drag findings do not block v1. The release chain is M0 through M4, then M6;
M5 stays deferred.

Later `software/` contains boot/runtime/demo assembly; `images/memory/` holds
deterministic byte images, listings, symbols, and bank-origin manifests. The
reference CPU model is test tooling, never the delivered CPU. Check each issue's
observable demonstration and evidence before closing it; implemented code or a
merged change alone does not prove a desktop gate.
