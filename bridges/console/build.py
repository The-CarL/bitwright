#!/usr/bin/env python3
"""Compile and test the bridge using JDK 21 and a pinned Logisim 5.0.0 JAR.

Only the Python standard library and the JDK are needed. No network accesses.
"""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent
VERSION = "0.1.0"


def run(command: list[str]) -> None:
    subprocess.run(command, check=True, timeout=120)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--logisim-jar", type=Path, required=True)
    parser.add_argument("--jdk-home", type=Path, default=os.environ.get("JAVA_HOME"))
    parser.add_argument("--output", type=Path, default=ROOT.parents[1] / "build" / "bitwright-console.jar")
    args = parser.parse_args()
    jar = args.logisim_jar.resolve()
    with zipfile.ZipFile(jar) as source:
        manifest = source.read("META-INF/MANIFEST.MF").decode("utf-8")
    if "Implementation-Version: 5.0.0\n" not in manifest.replace("\r\n", "\n"):
        parser.error("the bridge requires a Logisim-evolution 5.0.0 JAR")

    def executable(name: str) -> str:
        suffix = ".exe" if os.name == "nt" else ""
        path = args.jdk_home / "bin" / (name + suffix) if args.jdk_home else shutil.which(name)
        if not path or not Path(path).is_file():
            parser.error(f"cannot find {name}; set --jdk-home to a JDK 21 directory")
        return str(path)

    javac, java = executable("javac"), executable("java")
    version = subprocess.run([javac, "-version"], check=True, capture_output=True, text=True).stdout.strip()
    if not version.startswith("javac 21."):
        parser.error(f"JDK 21 is required for reproducible bytecode, found {version!r}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="bitwright-bridge-") as tmp:
        tmp_path = Path(tmp)
        classes, tests = tmp_path / "classes", tmp_path / "tests"
        classes.mkdir()
        tests.mkdir()
        sources = sorted((ROOT / "src" / "main" / "java").rglob("*.java"))
        run([javac, "--release", "21", "-encoding", "UTF-8", "-g:none", "-classpath", str(jar),
             "-d", str(classes), *map(str, sources)])
        test_sources = sorted((ROOT / "src" / "test" / "java").rglob("*.java"))
        classpath = os.pathsep.join([str(jar), str(classes)])
        run([javac, "--release", "21", "-encoding", "UTF-8", "-g:none", "-classpath", classpath,
             "-d", str(tests), *map(str, test_sources)])
        run([java, "-Djava.awt.headless=true", f"-Djava.util.prefs.userRoot={tmp_path / 'prefs'}",
             "-cp", os.pathsep.join([classpath, str(tests)]), "org.bitwright.console.ConsoleTests"])
        entries = {path.relative_to(classes).as_posix(): path.read_bytes()
                   for path in classes.rglob("*.class")}
        entries["META-INF/MANIFEST.MF"] = (
            "Manifest-Version: 1.0\r\n"
            "Library-Class: org.bitwright.console.ConsoleLibrary\r\n"
            "Implementation-Title: Bitwright ASCII / pixel host adapter\r\n"
            f"Implementation-Version: {VERSION}\r\n"
            "Logisim-Version: 5.0.0\r\n\r\n"
        ).encode("ascii")
        # Sorted entries, fixed timestamps/permissions, no host paths or compression variability.
        with zipfile.ZipFile(args.output, "w", compression=zipfile.ZIP_STORED) as output:
            for name, content in sorted(entries.items()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                output.writestr(info, content)
    digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
    print(f"Built {args.output}\nSHA256 {digest}")


if __name__ == "__main__":
    main()
