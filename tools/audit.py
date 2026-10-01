"""Recursively enforce Bitwright's primitive and portable-library policy."""
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as ET

from logisim import VerificationError

ALLOWED = {
    "#Wiring": {"Pin", "Probe", "Tunnel", "Splitter", "Constant", "Clock"},
    "#Gates": {"Buffer", "NOT Gate", "AND Gate", "OR Gate", "NAND Gate", "NOR Gate", "XOR Gate", "XNOR Gate"},
    "#Memory": {"D Flip-Flop", "RAM", "ROM"},
    "#I/O": {"Keyboard", "TTY", "RGB Video", "LED", "Button"},
    "#Base": {"Text"},
}


def audit(paths: list[Path], root: Path, *, require_jars: bool = True) -> dict[str, int]:
    root = root.resolve()
    seen: set[Path] = set()
    counts: Counter[str] = Counter()

    def portable(parent: Path, name: str) -> Path:
        if Path(name).is_absolute():
            raise VerificationError(f"Absolute library path in {parent}: {name}")
        target = (parent.parent / name).resolve()
        if not target.is_relative_to(root):
            raise VerificationError(f"Library escapes package: {name} in {parent}")
        return target

    def visit(path: Path) -> None:
        path = path.resolve()
        if path in seen:
            return
        if not path.is_file():
            raise VerificationError(f"Missing native library: {path}")
        seen.add(path)
        try:
            project = ET.parse(path).getroot()
        except ET.ParseError as exc:
            raise VerificationError(f"Invalid circuit XML: {path}: {exc}") from exc
        if project.tag != "project" or project.get("source") != "5.0.0":
            raise VerificationError(f"Unpinned/non-native circuit: {path}")
        libraries = {lib.get("name"): lib.get("desc", "") for lib in project.findall("lib")}
        for desc in libraries.values():
            if desc.startswith("jar#"):
                parts = desc.split("#")
                if len(parts) != 3 or parts[2] != "org.bitwright.bridge.BitwrightLibrary":
                    raise VerificationError(f"Unapproved host library: {desc}")
                target = portable(path, parts[1])
                if require_jars and not target.is_file():
                    raise VerificationError(f"Missing host library: {target}; build the bridge first.")
        local = {c.get("name") for c in project.findall("circuit")}
        for circuit in project.findall("circuit"):
            for comp in circuit.findall("comp"):
                name = comp.get("name", "")
                lib = comp.get("lib")
                if lib is None:
                    if name not in local:
                        raise VerificationError(f"Undefined local circuit {name} in {path}")
                    continue
                desc = libraries.get(lib, "")
                if desc.startswith("file#"):
                    target = portable(path, desc[5:])
                    visit(target)
                    names = {c.get("name") for c in ET.parse(target).getroot().findall("circuit")}
                    if name not in names:
                        raise VerificationError(f"Missing circuit {name} in {target}")
                elif desc.startswith("jar#"):
                    parts = desc.split("#")
                    if len(parts) != 3 or parts[2] != "org.bitwright.bridge.BitwrightLibrary":
                        raise VerificationError(f"Unapproved host library: {desc}")
                    target = portable(path, parts[1])
                    if require_jars and not target.is_file():
                        raise VerificationError(f"Missing host library: {target}; build the bridge first.")
                    if name != "BitwrightCanvas":
                        raise VerificationError(f"Unapproved Java component: {name}")
                    counts["HOST:" + name] += 1
                elif name not in ALLOWED.get(desc, set()):
                    raise VerificationError(f"Prohibited component {desc}/{name} in {path}:{circuit.get('name')}")
                else:
                    counts[desc + "/" + name] += 1
        # Libraries can contain disallowed definitions even when not currently instantiated.
        for desc in libraries.values():
            if desc.startswith("file#"):
                visit(portable(path, desc[5:]))

    for path in paths:
        visit(path)
    counts["native_files"] = len(seen)
    return dict(sorted(counts.items()))
