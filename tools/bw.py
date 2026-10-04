#!/usr/bin/env python3
"""Build and verify Bitwright's native Apple-1-inspired gate computer."""
from __future__ import annotations

import argparse
import errno
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import zipfile

if sys.version_info < (3, 12):
    raise SystemExit("Bitwright tools require Python 3.12 or newer; select .python-version.")

from audit import audit
from logisim import (ROOT, Result, VerificationError, check_tty, command, java_path, run,
                     fetch, validate_image, vectors, verify_jar)

EXPERIMENT = Path("experiments/mouse-canvas/workbench.circ")
PACKAGE_NAME = "bitwright-apple1"
# Explicit executable/source allowlist: optional bridge/pixel tooling never ships by accident.
CORE_FILES = (
    "README.md", "toolchain.json", ".python-version", "circuits/README.md",
    "circuits/bitwright.circ", "circuits/manual/foundations.circ",
    "circuits/generated/foundations.circ", "circuits/generated/ram-harness.circ",
    "circuits/generated/never-halt.circ", "images/memory/m0-ram.hex",
    "images/memory/m0-ram-wrong.hex", "images/memory/m0-ram.manifest.json",
    "tools/bw.py", "tools/audit.py", "tools/logisim.py",
    "tools/generate_circuits.py", "tools/java/RenderCircuit.java", "tools/java/M0TextSmoke.java",
    "circuits/terminal-bench.circ", "circuits/generated/cpu6502.circ",
    "circuits/generated/cpu6502-manifest.json", "circuits/generated/terminal.circ",
    "tools/asm6502.py", "tools/reference6502.py", "tools/build_software.py",
    "tools/generate_6502.py", "tools/generate_terminal.py", "tools/generate_machine.py",
    "tools/test_6502_differential.py", "tools/java/Cpu6502Smoke.java",
    "tools/java/TerminalSmoke.java", "tools/java/MachineSmoke.java", "tools/java/BitwrightMachineBenchmark.java",
    "bridges/console/build.py", "bridges/console/README.md", "build/bitwright-console.jar",
)


def checked(args: list[str], timeout: float = 60) -> Result:
    result = run(args, timeout=timeout)
    if result.returncode:
        raise VerificationError(result.stdout + result.stderr)
    print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())
    return result


def bridge() -> None:
    """Explicit optional experiment only; never called by terminal workflows."""
    script = ROOT / "bridges/build.py"
    if not script.is_file():
        raise VerificationError("The optional bridge is not included in the terminal package; use a source checkout.")
    args = [sys.executable, str(script), "--logisim-jar", str(verify_jar())]
    if os.environ.get("JAVA_HOME"):
        args += ["--jdk-home", os.environ["JAVA_HOME"]]
    checked(args)


def generate(check: bool = False, *, experiment: bool = False) -> None:
    checked([sys.executable, str(ROOT / "tools/generate_circuits.py"),
             *(["--check"] if check else []), *(["--experiment"] if experiment else [])])
    if not experiment:
        for script in ["build_software.py", "generate_6502.py", "generate_terminal.py", "generate_machine.py"]:
            checked([sys.executable, str(ROOT / "tools" / script), *(["--check"] if check else [])])


def console_bridge() -> None:
    args = [sys.executable, str(ROOT / "bridges/console/build.py"), "--logisim-jar", str(verify_jar())]
    if os.environ.get("JAVA_HOME"):
        args += ["--jdk-home", os.environ["JAVA_HOME"]]
    checked(args, timeout=120)


def primitive_audit(root: Path = ROOT, *, experiment: bool = False) -> dict[str, int]:
    paths = [root / EXPERIMENT] if experiment else sorted((root / "circuits").rglob("*.circ"))
    if not paths:
        raise VerificationError("No native terminal circuits found.")
    counts = audit(paths, root, experiment=experiment)
    print("Primitive audit:", json.dumps(counts, sort_keys=True))
    return counts


def ram_test(root: Path, *, negative: bool = False, name: str = "ram", prefix: list[str] = ()) -> None:
    path = root / "images/memory" / ("m0-ram-wrong.hex" if negative else "m0-ram.hex")
    validate_image(path, words=16)
    project = root / "circuits/generated/ram-harness.circ"
    result = run([*prefix, *command(str(project), "--tty", "table", "--load", str(path), "M0_RAM", headless=True)])
    result.save(ROOT / "build/test-results" / f"{name}.json")
    check_tty(result, project, "RamHarness", {"signature": 0x5a if negative else 0xa5, "pass": 0 if negative else 1})
    print(f"{name}: correct {'negative' if negative else 'positive'} signature ({result.seconds:.3f}s including startup)")


def terminal_echo(root: Path = ROOT, *, name: str = "terminal-echo", prefix: list[str] = (),
                  project: Path | None = None) -> None:
    project = project or root / "circuits/terminal-bench.circ"
    args = [*prefix, *command(str(project), "--tty", "tty", headless=True)]
    expected = "Bitwright M0\n"
    start = time.monotonic()
    with subprocess.Popen(args, cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, text=True, encoding="utf-8") as process:
        try:
            output, errors = process.communicate(expected, timeout=10)
        except subprocess.TimeoutExpired:
            # No halt pin in the interactive bench. This deadline includes startup;
            # it is not an input-latency measurement.
            process.kill()
            output, errors = process.communicate()
        else:
            raise VerificationError("Interactive echo bench unexpectedly terminated: " + errors)
        result = Result(args, process.returncode, output, errors, time.monotonic() - start)
    result.save(ROOT / "build/test-results" / f"{name}.json")
    if output != expected or errors.strip():
        raise VerificationError(f"Native Keyboard-to-TTY echo mismatch: {output!r}; {errors}")
    print(f"{name}: exact native ASCII echo; interactive process stopped at test deadline.")


def native_tools(root: Path = ROOT, *, experiment: bool = False) -> list[str]:
    jar = verify_jar()
    bridge_jar = root / "build/bitwright-console.jar"
    if not experiment and not bridge_jar.is_file():
        raise VerificationError(f"Missing console library in tested package: {bridge_jar}")
    classes = root / "build" / ("experiment-tools" if experiment else "tools")
    classes.mkdir(parents=True, exist_ok=True)
    sources = [root / "tools/java/RenderCircuit.java"]
    sources += [root / ("tools/java/experiments/M0PixelSmoke.java" if experiment else "tools/java/M0TextSmoke.java")]
    if not experiment:
        sources += [root / "tools/java" / name for name in ("Cpu6502Smoke.java", "TerminalSmoke.java", "MachineSmoke.java", "BitwrightMachineBenchmark.java")]
    classpath = os.pathsep.join([str(jar), str(bridge_jar)])
    checked([java_path("javac"), "--release", "21", "-encoding", "UTF-8", "-g:none",
             "-cp", classpath, "-d", str(classes), *map(str, sources)])
    return [java_path(), "-Djava.awt.headless=true",
            f"-Djava.util.prefs.userRoot={root / 'build/java-preferences'}",
            "-cp", os.pathsep.join([classpath, str(classes)])]


def native_artifacts() -> None:
    """Native text checks and artifact rendering, independent of optional graphics."""
    args = native_tools()
    result = checked([*args, "M0TextSmoke", str(ROOT / "circuits/terminal-bench.circ")])
    result.save(ROOT / "build/test-results/native-text.json")
    for project, circuit, name in [
        ("terminal-bench.circ", "M0Workbench", "m0-terminal"),
        ("bitwright.circ", "Bitwright", "bitwright"),
        ("generated/terminal.circ", "Apple1Console", "apple1-console"),
        ("generated/foundations.circ", "LoadBit", "load-bit"),
        ("manual/foundations.circ", "LoadBit", "manual-load-bit"),
        ("generated/ram-harness.circ", "RamHarness", "ram-harness"),
    ]:
        checked([*args, "RenderCircuit", str(ROOT / "circuits" / project), circuit,
                 str(ROOT / "build/renders" / f"{name}.png")])


def test_experiment() -> None:
    generate(check=True, experiment=True)
    bridge()
    primitive_audit(experiment=True)
    vectors(ROOT / EXPERIMENT, "M0Workbench", ROOT / "experiments/mouse-canvas/workbench-reset.txt",
            log="experiment-workbench-reset")
    args = native_tools(experiment=True)
    result = checked([*args, "M0PixelSmoke", str(ROOT / EXPERIMENT)])
    result.save(ROOT / "build/test-results/experiment-native-pixels.json")
    checked([*args, "RenderCircuit", str(ROOT / EXPERIMENT), "M0Workbench",
             str(ROOT / "build/experiment-renders/mouse-canvas.png")])
    print("Optional experiment checks passed; they are not terminal-v1 acceptance.")


def test_legacy() -> None:
    checked([sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"])
    generate(check=True)
    primitive_audit()
    native_artifacts()
    for source in ["manual", "generated"]:
        project = ROOT / "circuits" / source / "foundations.circ"
        for name, vector in [("GateAnd", "and"), ("LoadBit", "load-bit")]:
            result = vectors(project, name, ROOT / "tests/vectors" / f"{vector}.txt", log=f"{source}-{vector}")
            print(f"{source}/{name}: pass ({result.seconds:.3f}s including startup)")
    vectors(ROOT / "circuits/generated/foundations.circ", "GateAnd",
            ROOT / "tests/vectors/intentional-fail.txt", negative=True, log="intentional-failure")
    print("Incorrect vector rejected despite Logisim exit status zero.")
    vectors(ROOT / "circuits/terminal-bench.circ", "TerminalControl", ROOT / "tests/vectors/terminal-control.txt", log="terminal-control")
    vectors(ROOT / "circuits/terminal-bench.circ", "M0Workbench", ROOT / "tests/vectors/workbench-reset.txt", log="workbench-reset")
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
    print("Automated terminal M0 tests passed. Desktop acceptance is recorded separately.")


def roundtrip() -> None:
    folder = ROOT / "build/roundtrip"
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
    original = ROOT / "circuits/terminal-bench.circ"
    saved = folder / "workbench.circ"
    saved.unlink(missing_ok=True)
    result = run(command("--new-file-format", str(original), str(saved)))
    result.save(ROOT / "build/test-results/roundtrip-workbench.json")
    if result.returncode or not saved.is_file():
        raise VerificationError("Native workbench save failed: " + result.stdout + result.stderr)
    # The serializer must rebase relative native-library references for the new
    # destination. Resolve every declared library, including unused ones, before
    # testing the reopened project so a stale/missing dependency cannot hide.
    audit([saved], ROOT)
    for circuit, vector in [("TerminalControl", "terminal-control"), ("M0Workbench", "workbench-reset")]:
        vectors(saved, circuit, ROOT / "tests/vectors" / f"{vector}.txt", log=f"roundtrip-{vector}")
    terminal_echo(project=saved, name="roundtrip-terminal-echo")
    print("Native save/reopen behavior passed for both foundation sources and the terminal workbench.")
    original = ROOT / "circuits/bitwright.circ"
    saved = folder / "computer.circ"
    saved.unlink(missing_ok=True)
    result = run(command("--new-file-format", str(original), str(saved)), timeout=120)
    result.save(ROOT / "build/test-results/roundtrip-computer.json")
    if result.returncode or not saved.is_file():
        raise VerificationError("Native computer save failed: " + result.stdout + result.stderr)
    audit([saved], ROOT)
    machine_test(project=saved, name="roundtrip-computer-boot", boot_only=True)


def machine_test(root: Path = ROOT, *, project: Path | None = None, name: str = "machine",
                 boot_only: bool = False, prefix: list[str] = ()) -> Result:
    args = native_tools(root)
    result = checked([*prefix, *args, "MachineSmoke", str(project or root / "circuits/bitwright.circ"),
                      str(root), *(["--boot-only"] if boot_only else [])], timeout=180 if boot_only else 1200)
    result.save(ROOT / "build/test-results" / f"{name}.json")
    if "Native machine:" not in result.stdout or (not boot_only and "assertions passed" not in result.stdout):
        raise VerificationError("Missing explicit native machine success evidence")
    return result


def test() -> None:
    console_bridge()
    test_legacy()
    args = native_tools()
    for main, project in [("Cpu6502Smoke", "cpu6502.circ"), ("TerminalSmoke", "terminal.circ")]:
        result = checked([*args, main, str(ROOT / "circuits/generated" / project)], timeout=120)
        result.save(ROOT / "build/test-results" / f"{main}.json")
    from test_6502_differential import run_suite
    print("Independent native CPU comparison:", json.dumps(run_suite(), sort_keys=True))
    machine_test()
    print("Native computer regression suite passed; see the evidence report for desktop/performance limits.")


def package_files(root: Path = ROOT) -> dict[str, bytes]:
    files = {root / name for name in CORE_FILES}
    for folder in ["architecture", "docs"]:
        files.update((root / folder).rglob("*.md"))
        files.update((root / folder).rglob("*.json"))
        files.update((root / folder).rglob("*.svg"))
        files.update((root / folder).rglob("*.png"))
    files.update((root / "software").rglob("*.asm"))
    files.update((root / "bridges/console/src").rglob("*.java"))
    files.update((root / "images/memory").glob("6502-*"))
    files.update((root / "tests").glob("test_*.py"))
    files.update((root / "tests/vectors").glob("*.txt"))
    snapshot = {}
    for path in sorted(files):
        if not path.is_file():
            raise VerificationError(f"Missing package input: {path}")
        snapshot[path.relative_to(root).as_posix()] = path.read_bytes()
    return snapshot


def package_bytes(files: dict[str, bytes]) -> bytes:
    manifest = {name: hashlib.sha256(content).hexdigest() for name, content in sorted(files.items())}
    entries = dict(files)
    entries["SHA256SUMS.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
    destination = io.BytesIO()
    with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in sorted(entries.items()):
            item = zipfile.ZipInfo(PACKAGE_NAME + "/" + name, date_time=(2026, 10, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.create_system = 3
            item.external_attr = 0o100644 << 16
            archive.writestr(item, content)
    return destination.getvalue()


def verify_package(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        if archive.testzip() is not None:
            raise VerificationError("ZIP integrity check failed.")
        names = archive.namelist()
        prefix = PACKAGE_NAME + "/"
        if len(set(names)) != len(names) or any(not n.startswith(prefix) or ".." in Path(n).parts for n in names):
            raise VerificationError("Invalid or duplicate package member paths.")
        manifest = json.loads(archive.read(prefix + "SHA256SUMS.json"))
        if set(names) != {prefix + n for n in manifest} | {prefix + "SHA256SUMS.json"}:
            raise VerificationError("Package contents differ from the checksum manifest.")
        for name, expected in manifest.items():
            actual = hashlib.sha256(archive.read(prefix + name)).hexdigest()
            if actual != expected:
                raise VerificationError(f"Package checksum mismatch: {name}")


def package() -> Path:
    console_bridge()
    generate(check=True)
    primitive_audit()
    files = package_files()
    contents = package_bytes(files)
    if contents != package_bytes(dict(reversed(list(files.items())))):
        raise VerificationError("Package generation is not deterministic.")
    target = ROOT / "dist" / f"{PACKAGE_NAME}.zip"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contents)
    verify_package(target)
    with tempfile.TemporaryDirectory(prefix="bitwright-relocated-") as temp:
        with zipfile.ZipFile(target) as archive:
            archive.extractall(temp)
        relocated = Path(temp) / PACKAGE_NAME
        primitive_audit(relocated)
        ram_test(relocated, name="relocated-ram")
        terminal_echo(relocated, name="relocated-terminal-echo")
        machine_test(relocated, name="relocated-computer-boot", boot_only=True)
    print(f"{target}\nSHA256 {hashlib.sha256(contents).hexdigest()}")
    return target


def network_isolator() -> list[str]:
    if sys.platform == "darwin" and shutil.which("sandbox-exec"):
        return [shutil.which("sandbox-exec"), "-p", "(version 1)(allow default)(deny network*)"]
    if sys.platform.startswith("linux") and shutil.which("unshare"):
        return [shutil.which("unshare"), *(["--user", "--map-root-user"] if os.geteuid() else []), "--net"]
    raise VerificationError("Per-process network denial is unavailable on this platform; no offline result is claimed.")


def offline_test() -> None:
    """Check the extracted package under process-local network denial, never alter host networking."""
    target = ROOT / "dist" / f"{PACKAGE_NAME}.zip"
    if not target.is_file():
        raise VerificationError("Build the terminal package before offline-test.")
    verify_package(target)
    prefix = network_isolator()
    # A reachable local endpoint provides a deterministic negative control without
    # depending on an external service, DNS, or the machine's connectivity.
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen(2)
        port = listener.getsockname()[1]
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            pass
        probe = ("import json,os,socket,sys\ntry:\n"
                 f" socket.create_connection(('127.0.0.1',{port}),timeout=2).close()\n"
                 "except OSError as e:\n print(json.dumps({'blocked':True,'errno':e.errno,'netns':os.stat('/proc/self/ns/net').st_ino if sys.platform.startswith('linux') else None}))\n"
                 "else:\n print(json.dumps({'blocked':False}));sys.exit(2)\n")
        result = run([*prefix, sys.executable, "-c", probe])
        result.save(ROOT / "build/test-results/offline-denial-control.json")
        try:
            control = json.loads(result.stdout)
        except ValueError:
            control = {}
        if sys.platform == "darwin":
            verified = control.get("errno") in (errno.EPERM, errno.EACCES)
        elif sys.platform.startswith("linux"):
            verified = control.get("netns") is not None and control["netns"] != os.stat("/proc/self/ns/net").st_ino
        else:
            verified = False
        if result.returncode or not control.get("blocked") or not verified:
            raise VerificationError("Network isolation could not be established; no offline pass: " + result.stdout + result.stderr)

    with tempfile.TemporaryDirectory(prefix="bitwright-offline-") as temp:
        with zipfile.ZipFile(target) as archive:
            archive.extractall(temp)
        relocated = Path(temp) / PACKAGE_NAME
        primitive_audit(relocated)
        ram_test(relocated, name="offline-ram", prefix=prefix)
        terminal_echo(relocated, name="offline-terminal-echo", prefix=prefix)
        machine_test(relocated, name="offline-computer-boot", boot_only=True, prefix=prefix)
    print("Extracted computer package passed firmware boot and native RAM/ASCII tests with verified network denial.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["fetch", "doctor", "build", "generate", "check-generated", "audit", "test", "test-machine", "test-legacy", "benchmark", "render", "roundtrip", "package", "offline-test", "run", "run-bench", "bridge", "console-bridge", "test-experiment", "audit-experiment", "run-experiment"])
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
        elif args.action == "build":
            console_bridge()
            generate()
            primitive_audit()
        elif args.action == "check-generated":
            generate(check=True)
        elif args.action == "bridge":
            bridge()
        elif args.action == "console-bridge":
            console_bridge()
        elif args.action == "audit":
            primitive_audit()
        elif args.action == "audit-experiment":
            primitive_audit(experiment=True)
        elif args.action == "test-experiment":
            test_experiment()
        elif args.action == "test":
            test()
        elif args.action == "test-machine":
            machine_test()
        elif args.action == "benchmark":
            checked([*native_tools(), "BitwrightMachineBenchmark", str(ROOT / "circuits/bitwright.circ"),
                     str(ROOT / "build/test-results/machine-benchmark.json")], timeout=180)
        elif args.action == "test-legacy":
            test_legacy()
        elif args.action == "render":
            primitive_audit()
            native_artifacts()
        elif args.action == "roundtrip":
            roundtrip()
        elif args.action == "package":
            package()
        elif args.action == "offline-test":
            offline_test()
        elif args.action in {"run", "run-bench", "run-experiment"}:
            project = ROOT / (EXPERIMENT if args.action == "run-experiment" else "circuits/terminal-bench.circ" if args.action == "run-bench" else "circuits/bitwright.circ")
            primitive_audit(experiment=args.action == "run-experiment")
            return subprocess.call(command(str(project)))
    except (VerificationError, OSError, ValueError, zipfile.BadZipFile) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
