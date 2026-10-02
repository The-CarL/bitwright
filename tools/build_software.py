#!/usr/bin/env python3
"""Deterministically assemble committed monitor/demo artifacts; --check is read-only."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from asm6502 import LENGTHS, OPCODES, assemble, write_outputs

ROOT = Path(__file__).resolve().parents[1]


def build(check=False, root=ROOT):
    root = Path(root)
    generated = []
    with tempfile.TemporaryDirectory(prefix="bitwright-6502-") as temporary:
        destination = Path(temporary)
        plans = [("software/monitor/monitor.asm", "6502-monitor", 0xF000, 0x10000, 0xFF00, 255)]
        plans += [(f"software/demos/{name}.asm", f"6502-{name}", None, None, 0x0300, 0)
                  for name in ("hello", "sum", "memory")]
        for source, name, start, end, entry, fill in plans:
            result = assemble((root / source).read_text())
            write_outputs(result, destination / "images/memory" / name,
                          start, end, entry, source, fill)
        table = {"architecture": "original NMOS 6502 documented instructions",
                 "source": "https://syncopate.us/books/Synertek6502ProgrammingManual.html#B",
                 "encodings": [{"opcode": code, "hex": f"{code:02X}", "mnemonic": name,
                                "mode": mode, "bytes": LENGTHS[mode]}
                               for (name, mode), code in sorted(OPCODES.items(), key=lambda pair: pair[1])]}
        opcode_file = destination / "architecture/6502-opcodes.json"
        opcode_file.parent.mkdir(parents=True, exist_ok=True)
        opcode_file.write_text(json.dumps(table, indent=2) + "\n")
        stale = []
        for path in sorted(destination.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(destination)
            target = root / relative
            generated.append(str(relative))
            if check:
                if not target.exists() or target.read_bytes() != path.read_bytes():
                    stale.append(str(relative))
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(path.read_bytes())
        if stale:
            raise RuntimeError("stale generated software artifacts: " + ", ".join(stale))
    return generated


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        artifacts = build(args.check)
    except (ValueError, RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(f"{'Verified' if args.check else 'Generated'} {len(artifacts)} deterministic software artifacts")


if __name__ == "__main__":
    main()
