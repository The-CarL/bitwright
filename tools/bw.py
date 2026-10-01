#!/usr/bin/env python3
"""Bitwright development commands. Release readers only need Logisim."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import zipfile

if sys.version_info < (3, 12):
    raise SystemExit("Bitwright tools require Python 3.12 or newer; select the version in .python-version.")

from audit import audit
from logisim import (ROOT, Result, VerificationError, check_tty, command, fetch, java_path, run,
                     validate_image, vectors, verify_jar)


def checked(args: list[str], timeout: float = 60):
    result = run(args, timeout=timeout)
    if result.returncode:
        raise VerificationError(result.stdout + result.stderr)
    print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result


def bridge() -> None:
    args = [sys.executable, str(ROOT / "bridges" / "build.py"), "--logisim-jar", str(verify_jar())]
    if os.environ.get("JAVA_HOME"):
        args += ["--jdk-home", os.environ["JAVA_HOME"]]
    checked(args)


def generate(check: bool = False) -> None:
    checked([sys.executable, str(ROOT / "tools" / "generate_circuits.py"), *(["--check"] if check else [])])


def primitive_audit(root: Path = ROOT) -> dict[str, int]:
    counts = audit(sorted((root / "circuits").rglob("*.circ")), root)
    print("Primitive audit:", json.dumps(counts, sort_keys=True))
    return counts


def ram_test(root: Path, *, negative: bool = False, name: str = "ram") -> None:
    path = root / "images" / "memory" / ("m0-ram-wrong.hex" if negative else "m0-ram.hex")
    validate_image(path, words=16)
    project = root / "circuits" / "generated" / "ram-harness.circ"
    result = run(command(str(project), "--tty", "table", "--load", str(path), "M0_RAM", headless=True))
    result.save(ROOT / "build" / "test-results" / f"{name}.json")
    check_tty(result, project, "RamHarness", {"signature": 0x5a if negative else 0xa5, "pass": 0 if negative else 1})
    print(f"{name}: correct {'negative' if negative else 'positive'} signature, {result.seconds:.3f}s including startup")


def terminal_echo() -> None:
    args = command(str(ROOT / "circuits/bitwright.circ"), "--tty", "tty", headless=True)
    expected = "Bitwright M0\n"
    start = time.monotonic()
    with subprocess.Popen(args, cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True) as process:
        try:
            output, errors = process.communicate(expected, timeout=3)
        except subprocess.TimeoutExpired:
            # This interactive bench intentionally has no halt pin.
            process.kill()
            output, errors = process.communicate()
        else:
            raise VerificationError("Interactive echo bench unexpectedly terminated: " + errors)
        result = Result(args, process.returncode, output, errors, time.monotonic() - start)
    result.save(ROOT / "build/test-results/terminal-echo.json")
    if output != expected or errors.strip():
        raise VerificationError(f"Native Keyboard-to-TTY echo mismatch: {output!r}; {errors}")
    print("Native Keyboard-to-TTY ASCII path echoed exactly; interactive process stopped by test deadline.")


def native_artifacts() -> None:
    """Exercise native pixels and render circuit artifacts without controlling the desktop."""
    jar = verify_jar()
    compiler = str(Path(os.environ["JAVA_HOME"]) / "bin/javac") if os.environ.get("JAVA_HOME") else "javac"
    classes = ROOT / "build/tools"
    classes.mkdir(parents=True, exist_ok=True)
    checked([compiler, "-cp", str(jar), "-d", str(classes),
             *map(str, sorted((ROOT / "tools/java").glob("*.java")))])
    args = [java_path(), "-Djava.awt.headless=true", "-cp", os.pathsep.join([str(jar), str(classes)])]
    result = checked([*args, "M0PixelSmoke", str(ROOT / "circuits/bitwright.circ")])
    result.save(ROOT / "build/test-results/native-pixels.json")
    for project, circuit, name in [
        ("bitwright.circ", "M0Workbench", "m0-workbench"),
        ("generated/foundations.circ", "LoadBit", "load-bit"),
        ("manual/foundations.circ", "LoadBit", "manual-load-bit"),
        ("generated/ram-harness.circ", "RamHarness", "ram-harness"),
    ]:
        checked([*args, "RenderCircuit", str(ROOT / "circuits" / project), circuit,
                 str(ROOT / "build/renders" / f"{name}.png")])


def test() -> None:
    checked([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    generate(check=True)
    bridge()
    primitive_audit()
    native_artifacts()
    for source in ["manual", "generated"]:
        project = ROOT / "circuits" / source / "foundations.circ"
        for name, vector in [("GateAnd", "and"), ("LoadBit", "load-bit")]:
            result = vectors(project, name, ROOT / "tests" / "vectors" / f"{vector}.txt", log=f"{source}-{vector}")
            print(f"{source}/{name}: pass ({result.seconds:.3f}s including startup)")
    vectors(ROOT / "circuits/generated/foundations.circ", "GateAnd",
            ROOT / "tests/vectors/intentional-fail.txt", negative=True, log="intentional-failure")
    print("Incorrect vector rejected despite Logisim exit status zero.")
    vectors(ROOT / "circuits/bitwright.circ", "M0Workbench", ROOT / "tests/vectors/workbench-reset.txt", log="workbench-reset")
    # These are parser/setup errors, not expected circuit failures.
    with tempfile.TemporaryDirectory(prefix="bitwright-invalid-") as tmp:
        missing = Path(tmp) / "missing-pin.txt"
        missing.write_text("NotAPin Y\n0 0\n")
        try:
            vectors(ROOT / "circuits/generated/foundations.circ", "GateAnd", missing, log="missing-pin")
        except VerificationError as exc:
            if "Missing or ambiguous vector summary" not in str(exc):
                raise
        else:
            raise VerificationError("Missing pin was not rejected.")
        invalid = Path(tmp) / "invalid.hex"
        invalid.write_text("v2.0 raw\nnot-a-byte\n")
        try:
            validate_image(invalid)
        except VerificationError:
            pass
        else:
            raise VerificationError("Malformed image was not rejected.")
    ram_test(ROOT)
    ram_test(ROOT, negative=True, name="ram-negative")
    terminal_echo()
    try:
        run(command(str(ROOT / "circuits/generated/never-halt.circ"), "--tty", "table", headless=True), timeout=2)
    except VerificationError as exc:
        if "Timed out" not in str(exc):
            raise
    else:
        raise VerificationError("Nonterminating simulator escaped the watchdog.")
    print("Nonterminating simulator rejected by timeout.")
    roundtrip()
    print("Automated M0 tests passed. See docs/evidence for separate desktop acceptance.")


def roundtrip() -> None:
    folder = ROOT / "build" / "roundtrip"
    folder.mkdir(parents=True, exist_ok=True)
    for source in ["manual", "generated"]:
        original = ROOT / "circuits" / source / "foundations.circ"
        saved = folder / f"{source}.circ"
        saved.unlink(missing_ok=True)
        result = run(command("--new-file-format", str(original), str(saved)))
        result.save(ROOT / "build/test-results" / f"roundtrip-{source}.json")
        if result.returncode or not saved.is_file():
            raise VerificationError("Native save failed: " + result.stdout + result.stderr)
        for name, vector in [("GateAnd", "and"), ("LoadBit", "load-bit")]:
            vectors(saved, name, ROOT / "tests/vectors" / f"{vector}.txt", log=f"roundtrip-{source}-{vector}")
    print("Native load/save/reopen behavior passed for both circuit sources.")


def package() -> Path:
    generate(check=True)
    bridge()
    primitive_audit()
    target = ROOT / "dist" / "bitwright-m0.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    files = []
    for folder in ["circuits", "images", "architecture", "docs", "bridges", "tools", "tests"]:
        files.extend(p for p in (ROOT / folder).rglob("*")
                     if p.is_file() and not {"__pycache__", "build"}.intersection(p.relative_to(ROOT).parts)
                     and not p.name.endswith((".bak", ".autosave", ".pyc")))
    files += [ROOT / "README.md", ROOT / "toolchain.json", ROOT / ".python-version", ROOT / "build/bitwright-bridge.jar"]
    manifest = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            item = zipfile.ZipInfo("bitwright-m0/" + str(path.relative_to(ROOT)), date_time=(2026, 10, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, path.read_bytes())
        item = zipfile.ZipInfo("bitwright-m0/SHA256SUMS.json", date_time=(2026, 10, 1, 0, 0, 0))
        item.compress_type = zipfile.ZIP_DEFLATED
        item.create_system = 3
        item.external_attr = 0o100644 << 16
        archive.writestr(item, json.dumps(manifest, indent=2) + "\n")
    # Relocation is an actual simulator load, not just a ZIP content assertion.
    with tempfile.TemporaryDirectory(prefix="bitwright-relocated-") as temp:
        with zipfile.ZipFile(target) as archive:
            archive.extractall(temp)
        relocated = Path(temp) / "bitwright-m0"
        primitive_audit(relocated)
        ram_test(relocated, name="relocated-ram")
        result = run(command(str(relocated / "circuits/bitwright.circ"), "--tty", "stats", headless=True))
        result.save(ROOT / "build/test-results/relocated-library-load.json")
        if result.returncode or "Bitwright host canvas" not in result.stdout:
            raise VerificationError("Relocated native/JAR library load failed: " + result.stdout + result.stderr)
    print(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "doctor", "generate", "check-generated", "bridge", "audit", "test", "render", "roundtrip", "package", "run"])
    args = parser.parse_args()
    try:
        if args.action == "fetch":
            print(fetch())
        elif args.action == "doctor":
            print("Python", sys.version.split()[0])
            print("Pinned JAR", verify_jar())
            checked(command("--version"))
        elif args.action == "generate":
            generate()
        elif args.action == "check-generated":
            generate(check=True)
        elif args.action == "bridge":
            bridge()
        elif args.action == "audit":
            primitive_audit()
        elif args.action == "test":
            test()
        elif args.action == "render":
            bridge()
            native_artifacts()
        elif args.action == "roundtrip":
            roundtrip()
        elif args.action == "package":
            package()
        elif args.action == "run":
            return subprocess.call(command(str(ROOT / "circuits/bitwright.circ")))
    except (VerificationError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
