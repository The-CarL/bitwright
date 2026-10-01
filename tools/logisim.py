"""Pinned Logisim process boundary. Never equate exit code zero with a passing test."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
LOCK = json.loads((ROOT / "toolchain.json").read_text())


class VerificationError(RuntimeError):
    pass


@dataclass
class Result:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    seconds: float

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2) + "\n")


def run(command: list[str], *, timeout: float = 30, cwd: Path = ROOT) -> Result:
    start = time.monotonic()
    try:
        p = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise VerificationError(f"Timed out after {timeout:g}s: {command[0]}") from exc
    except OSError as exc:
        raise VerificationError(f"Cannot execute {command[0]}: {exc}") from exc
    return Result(command, p.returncode, p.stdout, p.stderr, time.monotonic() - start)


def jar_path() -> Path:
    return Path(os.environ.get("LOGISIM_JAR", ROOT / ".cache" / LOCK["logisim"]["filename"])).resolve()


def java_path(tool: str = "java") -> str:
    if os.environ.get("JAVA_HOME"):
        return str(Path(os.environ["JAVA_HOME"]) / "bin" / tool)
    return tool


def verify_jar(path: Path | None = None) -> Path:
    path = path or jar_path()
    if not path.is_file():
        raise VerificationError(f"Missing pinned simulator: {path}; run 'python3 tools/bw.py fetch'.")
    with path.open("rb") as stream:
        actual = hashlib.file_digest(stream, "sha256").hexdigest()
    if actual != LOCK["logisim"]["sha256"]:
        raise VerificationError(f"Simulator checksum mismatch: {actual}. Use the official standalone JAR.")
    return path


def fetch() -> Path:
    target = jar_path()
    if target.is_file():
        return verify_jar(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(".download")
    try:
        with urllib.request.urlopen(LOCK["logisim"]["url"], timeout=60) as response:
            with temporary.open("wb") as out:
                while chunk := response.read(1024 * 1024):
                    out.write(chunk)
        verify_jar(temporary)
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target


def command(*args: str, headless: bool = False) -> list[str]:
    # Logisim uses Java preferences even in CLI mode. Keep test settings local.
    prefs = ROOT / "build" / "java-preferences"
    prefs.mkdir(parents=True, exist_ok=True)
    return [java_path(), f"-Djava.util.prefs.userRoot={prefs}",
            *(["-Djava.awt.headless=true"] if headless else []),
            "-jar", str(verify_jar()), "--locale", "en", "--no-splash", *map(str, args)]


def vector_rows(path: Path) -> int:
    lines = [line.split("#", 1)[0].strip() for line in path.read_text().splitlines()]
    return max(0, len([line for line in lines if line]) - 1)


def check_vectors(result: Result, expected_rows: int, *, negative: bool = False) -> tuple[int, int]:
    if result.returncode != 0:
        raise VerificationError(f"Simulator exited {result.returncode}: {result.stderr[-2000:]}")
    summaries = re.findall(r"Passed:\s*(\d+),\s*Failed:\s*(\d+)", result.stdout)
    if len(summaries) != 1:
        raise VerificationError("Missing or ambiguous vector summary: " + (result.stdout + result.stderr)[-2000:])
    passed, failed = map(int, summaries[0])
    if expected_rows <= 0 or passed + failed != expected_rows:
        raise VerificationError(f"Incomplete vector run: expected {expected_rows}, got {passed}+{failed}.")
    errors = result.stdout + result.stderr
    if re.search(r"Error (loading|preparing)|Exception|not found|Could not|cannot load", errors, re.I):
        raise VerificationError("Simulator setup/runtime error: " + errors[-2000:])
    if negative:
        if failed == 0:
            raise VerificationError("Deliberately incorrect vector unexpectedly passed.")
    elif failed:
        raise VerificationError(f"{failed} of {expected_rows} vectors failed: {errors[-3000:]}")
    return passed, failed


def vectors(project: Path, circuit: str, path: Path, *, negative: bool = False,
            timeout: float = 60, log: str | None = None) -> Result:
    result = run(command("--test-vector", circuit, str(path), str(project)), timeout=timeout)
    if log:
        result.save(ROOT / "build" / "test-results" / f"{log}.json")
    check_vectors(result, vector_rows(path), negative=negative)
    return result


def validate_image(path: Path, *, width: int = 8, words: int | None = None) -> int:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "v2.0 raw":
        raise VerificationError(f"{path}: expected 'v2.0 raw' header.")
    count = 0
    for line in lines[1:]:
        for token in line.split("#", 1)[0].split():
            match = re.fullmatch(r"(?:(\d+)\*)?([0-9a-fA-F]+)", token)
            if not match:
                raise VerificationError(f"{path}: invalid memory word {token!r}.")
            repeat = int(match[1] or "1")
            value = int(match[2], 16)
            if repeat <= 0 or value >= 1 << width:
                raise VerificationError(f"{path}: memory word out of range: {token}.")
            count += repeat
    if not count or (words is not None and count != words):
        raise VerificationError(f"{path}: expected {words or 'nonempty'} words, got {count}.")
    return count


def check_tty(result: Result, project: Path, circuit_name: str, expected: dict[str, int]) -> None:
    """TTY clocked tables omit headers and halt; use native top-down pin ordering."""
    circuit = next((c for c in ET.parse(project).getroot().findall("circuit")
                    if c.get("name") == circuit_name), None)
    if circuit is None:
        raise VerificationError(f"Missing TTY circuit {circuit_name}.")
    pins = []
    halt = False
    for component in circuit.findall("comp"):
        if component.get("name") != "Pin":
            continue
        attrs = {a.get("name"): a.get("val") for a in component.findall("a")}
        if attrs.get("output") != "true":
            continue
        label = attrs.get("label")
        width = int(attrs.get("width", "1"))
        if label == "halt":
            halt = width == 1
            continue
        x, y = map(int, component.get("loc").strip("()").split(","))
        pins.append((y, x, label, width))
    pins.sort()
    labels = [p[2] for p in pins]
    if not halt or len(set(labels)) != len(labels) or set(labels) != set(expected):
        raise VerificationError("TTY harness must have halt and uniquely labelled expected output pins.")
    if result.returncode or not result.stdout.strip():
        raise VerificationError("TTY failed or returned no signature: " + result.stderr)
    final = None
    for line in result.stdout.strip().splitlines():
        words = [word.replace(" ", "") for word in line.split("\t")]
        if len(words) != len(pins):
            raise VerificationError(f"Unexpected TTY column count: {line!r}")
        # Transient unknowns are permitted before settling, never in the final result.
        final = words
    for (_, _, label, width), word in zip(pins, final):
        if not re.fullmatch(r"[01]+", word) or len(word) != width or int(word, 2) != expected[label]:
            raise VerificationError(f"TTY {label}: expected {expected[label]:x}/{width} bits, got {word!r}.")
