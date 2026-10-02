# Optional historical mouse and pixel workbench

This preserves Bitwright's original M0 mouse/pixel experiment. It is **outside the approved keyboard/text-only v1**. Its Java bridge, event queue, RGB display, and unresolved desktop interaction findings do not gate the default project.

`workbench.circ` is generated from `mouse_workbench()` in `../../tools/generate_circuits.py`. Regenerate explicitly with:

```sh
python3 tools/generate_circuits.py --experiment
python3 tools/generate_circuits.py --experiment --check
```

The flag adds this experiment to the normal generation/check set. Default generation/check does not require this file or its bridge. The native project keeps relative references to `../../build/bitwright-bridge.jar` and `../../circuits/manual/foundations.circ`; it must remain in this directory layout. Build the bridge through the explicit optional tooling before opening it. The experiment keeps the circuit name `M0Workbench`; its old reset vector is preserved as `workbench-reset.txt` here.

## Historical controls

Use the Poke tool and enable ticks. Start with a slow clock for observing packets; raise the frequency for live input. This does not establish measured responsiveness.

- Click stock Keyboard and type ASCII to echo to the TTY.
- Set manual X, Y, Color, and Plot to write pixels on stock RGB Video. Clear resets the image.
- Set a nonzero Color, Plot=1, and Ack=1, then press/drag inside the custom canvas. Primitive AND gates allow plotting only for a valid packet with the primary button held. Mouse coordinates feed the pixel-command bus; mouse events do not draw by themselves.
- With Ack=0, inspect the stable front mouse packet. Ack=1 consumes one packet on each falling clock edge. MouseOverflow and OverflowClear refer to the bounded host queue, not the future machine FIFO.
- Reset clears host queues and display state. No hover interface is promised.

Keep findings and limitations with the experiment. Passing Java/native checks does not prove desktop focus, drag, pause/resume, or release-outside behavior; do not describe this as a completed interactive computer.
