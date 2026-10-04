#!/usr/bin/env python3
"""Compare actual native gate CPU retirements and writes with the Python oracle.

The Java fixture only clocks circuits and supplies byte-array bus memory. All
instruction execution takes place in Cpu6502.circ. This suite covers every
documented encoding, pointer/page boundaries, taken/not-taken branches, decimal
edge cases, deterministic randomized operands, stack control and PC wrapping.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import random

from reference6502 import CPU6502, DECODE, B, C, D, I, N, U, V, Z

ROOT = Path(__file__).resolve().parents[1]


@dataclass
class Case:
    name: str
    start: int
    steps: int
    patches: list[tuple[int, bytes]]

    def line(self):
        return f"{self.name}\t{self.start:04x}\t{self.steps}\t" + ";".join(
            f"{address:04x}={data.hex()}" for address, data in self.patches)

    def expected(self):
        memory = bytearray(65536)
        for address, data in self.patches:
            for offset, value in enumerate(data):
                memory[(address + offset) & 65535] = value
        memory[0xFFFC], memory[0xFFFD] = self.start & 255, self.start >> 8
        cpu = CPU6502(memory)
        # Bitwright explicitly defines reset state; NMOS electrical power-up
        # register contents and reset bus cycles are outside this comparison.
        cpu.pc, cpu.sp, cpu.p = self.start, 0xFD, 0x24
        return [cpu.step() for _ in range(self.steps)]


def cases():
    suite = []
    operands = {"imp": [], "acc": [], "imm": [0x79], "rel": [5],
                "zp": [0x80], "zpx": [0xFE], "zpy": [0xFE],
                "abs": [0xFF, 0x20], "absx": [0xFF, 0x20],
                "absy": [0xFF, 0x20], "ind": [0xFF, 0x30],
                "indx": [0xFC], "indy": [0xFF]}
    memory = [(0, bytes([0x20, 0x81, 0, 0, 0, 0x42])), (0x80, b"\xa7"),
              (0xFF, b"\xff"), (0x20FF, b"\x7f"), (0x2102, b"\x81"),
              (0x2106, b"\x00"), (0x30FF, b"\x34"), (0x3000, b"\x50"),
              (0x3100, b"\x60"), (0x100, b"\x50"), (0x1FE, b"\x65\x34"),
              (0xFFFE, b"\x00\x50")]
    # Six preparation instructions set carry/overflow and exercise PHA/PLP.
    prefix = bytes([0xA9, U|I|C|V, 0x48, 0x28, 0xA9, 0xA5, 0xA2, 3, 0xA0, 7])
    for opcode, (mnemonic, mode) in sorted(DECODE.items()):
        code = prefix + bytes([opcode] + operands[mode])
        suite.append(Case(f"opcode_{opcode:02x}_{mnemonic}_{mode}", 0x4000, 7,
                          memory + [(0x4000, code)]))

    # Flags are pushed/pulled last, so each conditional branch sees exactly the
    # tested bit pattern. Both signs of branch displacement cross a page.
    for opcode, (mnemonic, mode) in sorted(DECODE.items()):
        if mode != "rel":
            continue
        for flags in (0x24, 0xE7):
            for delta in (0x7F, 0x80):
                code = bytes([0xA9, flags, 0x48, 0x28, opcode, delta])
                suite.append(Case(f"branch_{mnemonic}_{flags:02x}_{delta:02x}",
                                  0x40FB, 4, [(0x40FB, code)]))

    # Arithmetic setup: LDA left; SEC/CLC; SED/CLD; ADC/SBC #right.
    arithmetic = [(a, b, carry, True) for a, b in
                  [(0, 0), (0, 1), (9, 1), (0x49, 0x51), (0x50, 0x50),
                   (0x99, 1), (0x79, 0), (0x89, 0x76), (0xFF, 0xFF),
                   (0x0F, 0x0F), (0xFA, 0x0B), (0xA0, 0x0A)] for carry in (0, 1)]
    rng = random.Random(0x6502)
    arithmetic += [(rng.randrange(256), rng.randrange(256), rng.randrange(2), bool(i & 1))
                   for i in range(64)]
    for operation, opcode in [("ADC", 0x69), ("SBC", 0xE9)]:
        for index, (a, b, carry, decimal) in enumerate(arithmetic):
            code = bytes([0xA9, a, 0x38 if carry else 0x18, 0xF8 if decimal else 0xD8,
                          opcode, b])
            suite.append(Case(f"arithmetic_{operation}_{index:03d}", 0x4000, 4, [(0x4000, code)]))

    # Stack wrapping and PC wrapping are architectural, not timing assertions.
    suite += [
        Case("stack_wrap", 0x4000, 7, [(0x4000, bytes.fromhex("a2009aa95548a9aa6868"))]),
        Case("pc_wrap", 0xFFFE, 2, [(0xFFFE, bytes.fromhex("a942")), (0, b"\xea")]),
        Case("absolute_index_wrap", 0x4000, 2,
             [(0x4000, bytes.fromhex("a202bdffff")), (1, b"\xa5")]),
    ]
    return suite


def compare_output(stdout, suite):
    """Reject missing/duplicate/extra cases and truncated state output."""
    expected = {case.name: case.expected() for case in suite}
    actual, current = {}, None
    for line in stdout.splitlines():
        if line.startswith("CASE\t"):
            name = line.split("\t", 1)[1]
            if name not in expected or name in actual:
                raise AssertionError(f"unexpected or duplicate case {name}")
            actual[name], current = [], name
        elif line.startswith("STATE\t"):
            if current is None:
                raise AssertionError("state before case header")
            fields = line.split("\t")
            if len(fields) != 8:
                raise AssertionError(f"malformed native state: {line}")
            state = dict(zip(("pc", "a", "x", "y", "sp", "p"), map(int, fields[1:7])))
            writes = [tuple(map(int, pair.split(":"))) for pair in fields[7].split(",") if pair]
            actual[current].append({"after": state, "writes": writes})
    if set(actual) != set(expected):
        raise AssertionError(f"missing native cases: {sorted(set(expected) - set(actual))}")
    count = 0
    for name, traces in expected.items():
        if len(actual[name]) != len(traces):
            raise AssertionError(f"{name}: expected {len(traces)} retirements, got {len(actual[name])}")
        for index, (want, got) in enumerate(zip(traces, actual[name])):
            count += 1
            if want["after"] != got["after"] or want["writes"] != got["writes"]:
                raise AssertionError(f"{name} instruction {index} opcode {want['opcode']:02X}: "
                                     f"expected state {want['after']} writes {want['writes']}; got {got}")
    return count


def run_suite(root=ROOT, timeout=240):
    from logisim import VerificationError, java_path, run, verify_jar
    root = Path(root)
    jar = verify_jar()
    classes = root / "build/java"
    classes.mkdir(parents=True, exist_ok=True)
    compile_result = run([java_path("javac"), "-cp", str(jar), "-d", str(classes),
                          str(root / "tools/java/Cpu6502Smoke.java")], timeout=60, cwd=root)
    if compile_result.returncode:
        raise VerificationError(compile_result.stderr)
    suite = cases()
    result_dir = root / "build/test-results"
    result_dir.mkdir(parents=True, exist_ok=True)
    fixture = result_dir / "6502-differential-cases.txt"
    fixture.write_text("\n".join(case.line() for case in suite) + "\n")
    import os
    command = [java_path(), "-Djava.awt.headless=true", "-cp", os.pathsep.join((str(classes), str(jar))),
               "Cpu6502Smoke", str(root / "circuits/generated/cpu6502.circ"), "--cases", str(fixture)]
    result = run(command, timeout=timeout, cwd=root)
    result.save(result_dir / "6502-differential-process.json")
    if result.returncode:
        raise VerificationError(f"native CPU differential runner failed: {result.stderr[-4000:]}")
    instructions = compare_output(result.stdout, suite)
    report = {"cases": len(suite), "retirements": instructions, "documented_encodings": 151,
              "seconds": result.seconds, "writes_compared": True, "status": "pass"}
    (result_dir / "6502-differential.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeout", type=float, default=240)
    args = parser.parse_args()
    try:
        report = run_suite(timeout=args.timeout)
    except (AssertionError, RuntimeError, OSError) as exc:
        parser.exit(1, f"6502 differential test failed: {exc}\n")
    print(f"Native CPU differential: {report['cases']} cases, {report['retirements']} retirements, "
          f"151 documented encodings passed in {report['seconds']:.2f}s")


if __name__ == "__main__":
    main()
