#!/usr/bin/env python3
"""Small, dependency-free NMOS 6502 assembler.

All 151 documented encodings are accepted. Undocumented/65C02 instructions are
deliberately rejected. Forward references use absolute addressing unless forced
with ``z:expression``; ``a:expression`` forces absolute addressing. This policy
keeps instruction sizes stable without silently changing branches between passes.
Expressions support + - * // % << >> & | ^ ~, parentheses, $hex, %binary,
character literals, symbols, and prefix < / > for low / high byte. Expressions
are limited to 4096 characters, 256 syntax nodes and 64-bit integer magnitudes.
Opcode reference: MOS/Synertek MCS6500 Programming Manual (1976), appendix B.
"""
from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
import hashlib
import json
import operator
from pathlib import Path
import re
import sys


# Kept explicit: readers can compare every encoding with the published manual.
OPCODES = {}
_TABLE = """
ADC imm:69 zp:65 zpx:75 abs:6D absx:7D absy:79 indx:61 indy:71
AND imm:29 zp:25 zpx:35 abs:2D absx:3D absy:39 indx:21 indy:31
ASL acc:0A zp:06 zpx:16 abs:0E absx:1E
BCC rel:90
BCS rel:B0
BEQ rel:F0
BIT zp:24 abs:2C
BMI rel:30
BNE rel:D0
BPL rel:10
BRK imp:00
BVC rel:50
BVS rel:70
CLC imp:18
CLD imp:D8
CLI imp:58
CLV imp:B8
CMP imm:C9 zp:C5 zpx:D5 abs:CD absx:DD absy:D9 indx:C1 indy:D1
CPX imm:E0 zp:E4 abs:EC
CPY imm:C0 zp:C4 abs:CC
DEC zp:C6 zpx:D6 abs:CE absx:DE
DEX imp:CA
DEY imp:88
EOR imm:49 zp:45 zpx:55 abs:4D absx:5D absy:59 indx:41 indy:51
INC zp:E6 zpx:F6 abs:EE absx:FE
INX imp:E8
INY imp:C8
JMP abs:4C ind:6C
JSR abs:20
LDA imm:A9 zp:A5 zpx:B5 abs:AD absx:BD absy:B9 indx:A1 indy:B1
LDX imm:A2 zp:A6 zpy:B6 abs:AE absy:BE
LDY imm:A0 zp:A4 zpx:B4 abs:AC absx:BC
LSR acc:4A zp:46 zpx:56 abs:4E absx:5E
NOP imp:EA
ORA imm:09 zp:05 zpx:15 abs:0D absx:1D absy:19 indx:01 indy:11
PHA imp:48
PHP imp:08
PLA imp:68
PLP imp:28
ROL acc:2A zp:26 zpx:36 abs:2E absx:3E
ROR acc:6A zp:66 zpx:76 abs:6E absx:7E
RTI imp:40
RTS imp:60
SBC imm:E9 zp:E5 zpx:F5 abs:ED absx:FD absy:F9 indx:E1 indy:F1
SEC imp:38
SED imp:F8
SEI imp:78
STA zp:85 zpx:95 abs:8D absx:9D absy:99 indx:81 indy:91
STX zp:86 zpy:96 abs:8E
STY zp:84 zpx:94 abs:8C
TAX imp:AA
TAY imp:A8
TSX imp:BA
TXA imp:8A
TXS imp:9A
TYA imp:98
"""
for _line in _TABLE.strip().splitlines():
    _name, *_entries = _line.split()
    for _entry in _entries:
        _mode, _code = _entry.split(":")
        OPCODES[(_name, _mode)] = int(_code, 16)
LENGTHS = {m: 1 if m in ("imp", "acc") else 3 if m in
           ("abs", "absx", "absy", "ind") else 2 for _, m in OPCODES}


class AssemblyError(ValueError):
    """A diagnostic with source line context, never a partial successful build."""


class Unresolved(AssemblyError):
    pass


def split_fields(text: str, separator: str = ",") -> list[str]:
    """Split outside quoted strings (commas and semicolons can be ASCII data)."""
    parts, start, quote, escape = [], 0, None, False
    for i, ch in enumerate(text):
        if escape:
            escape = False
        elif quote and ch == "\\":
            escape = True
        elif quote and ch == quote:
            quote = None
        elif not quote and ch in "\"'":
            quote = ch
        elif not quote and ch == separator:
            parts.append(text[start:i].strip())
            if separator == ";":
                return parts  # Comment prose is not parsed as assembly syntax.
            start = i + 1
    if quote:
        raise AssemblyError("unterminated quoted string")
    parts.append(text[start:].strip())
    return parts


def expression(text: str, symbols: dict[str, int], pc: int = 0) -> int:
    text = text.strip()
    if not text:
        raise AssemblyError("missing expression")
    if len(text) > 4096:
        raise AssemblyError("expression exceeds 4096 characters")
    if text.startswith(("<", ">")):
        inner = text[1:].lstrip()
        if inner.startswith(("<", ">")):
            raise AssemblyError("nested byte-extraction prefixes are not supported")
        value = expression(inner, symbols, pc)
        return (value >> (8 if text[0] == ">" else 0)) & 255
    if text == "*":
        return pc
    # Replace numeric literals only outside quotes.
    tokens = re.split(r"('(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")", text)
    for i in range(0, len(tokens), 2):
        tokens[i] = re.sub(r"\$([0-9a-fA-F]+)", r"0x\1", tokens[i])
        # '%' at the beginning of an operand denotes binary; between two
        # operands it remains modulo, including expressions such as '15 % 1'.
        tokens[i] = re.sub(r"(^|[+\-*/&|^~(<>,])(\s*)%([01]+)", r"\g<1>\g<2>0b\g<3>", tokens[i])
    try:
        node = ast.parse("".join(tokens), mode="eval").body
    except (SyntaxError, ValueError, RecursionError) as exc:
        raise AssemblyError(f"invalid expression {text!r}") from exc
    if sum(1 for _ in ast.walk(node)) > 256:
        raise AssemblyError("expression exceeds 256 syntax nodes")
    binary = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
              ast.FloorDiv: operator.floordiv, ast.Mod: operator.mod,
              ast.LShift: operator.lshift, ast.RShift: operator.rshift,
              ast.BitAnd: operator.and_, ast.BitOr: operator.or_, ast.BitXor: operator.xor}
    unary = {ast.UAdd: operator.pos, ast.USub: operator.neg, ast.Invert: operator.invert}
    def bounded(value):
        if abs(value) > 0xFFFFFFFFFFFFFFFF:
            raise AssemblyError("expression intermediate exceeds 64-bit magnitude")
        return value
    def evaluate(n):
        if isinstance(n, ast.Constant) and type(n.value) is int:
            return bounded(n.value)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and len(n.value) == 1:
            value = ord(n.value)
            if value > 127:
                raise AssemblyError("only ASCII character literals are supported")
            return value
        if isinstance(n, ast.Name):
            if n.id.upper() not in symbols:
                raise Unresolved(f"undefined symbol {n.id}")
            return bounded(symbols[n.id.upper()])
        if isinstance(n, ast.BinOp) and type(n.op) in binary:
            right = evaluate(n.right)
            if isinstance(n.op, (ast.LShift, ast.RShift)) and not 0 <= right <= 63:
                raise AssemblyError("shift count must be in 0..63")
            return bounded(binary[type(n.op)](evaluate(n.left), right))
        if isinstance(n, ast.UnaryOp) and type(n.op) in unary:
            return bounded(unary[type(n.op)](evaluate(n.operand)))
        raise AssemblyError(f"unsupported expression {text!r}")
    try:
        return evaluate(node)
    except (ZeroDivisionError, OverflowError) as exc:
        raise AssemblyError(f"invalid arithmetic in {text!r}") from exc


def addressing(name, operand, symbols, pc):
    operand = operand.strip()
    if not operand:
        return ("acc" if (name, "acc") in OPCODES else "imp"), ""
    if operand.upper() == "A" and (name, "acc") in OPCODES:
        return "acc", ""
    if (name, "rel") in OPCODES:
        return "rel", operand
    if operand.startswith("#"):
        return "imm", operand[1:]
    match = re.fullmatch(r"\((.+),\s*[Xx]\)", operand)
    if match:
        return "indx", match[1]
    match = re.fullmatch(r"\((.+)\),\s*[Yy]", operand)
    if match:
        return "indy", match[1]
    if operand.startswith("(") and operand.endswith(")"):
        return "ind", operand[1:-1]
    parts = split_fields(operand)
    if len(parts) > 2 or (len(parts) == 2 and parts[1].upper() not in ("X", "Y")):
        raise AssemblyError(f"invalid operand {operand!r}")
    expr, suffix = parts[0], parts[1].lower() if len(parts) == 2 else ""
    force = None
    if expr[:2].lower() in ("z:", "a:"):
        force, expr = expr[0].lower(), expr[2:]
    short, long = "zp" + suffix, "abs" + suffix
    if force:
        return (short if force == "z" else long), expr
    try:
        value = expression(expr, symbols, pc)
    except Unresolved:
        value = 0x100
    if 0 <= value <= 255 and (name, short) in OPCODES:
        return short, expr
    # STX zp,Y and STY zp,X have no absolute indexed alternative.
    return (long if (name, long) in OPCODES else short), expr


@dataclass
class Assembly:
    memory: dict[int, int]
    symbols: dict[str, int]
    listing: list[str]

    def binary(self, start=None, end=None, fill=0) -> bytes:
        if not self.memory:
            raise AssemblyError("source emits no bytes")
        start = min(self.memory) if start is None else start
        end = max(self.memory) + 1 if end is None else end
        if not 0 <= start < end <= 65536 or not 0 <= fill <= 255:
            raise AssemblyError("invalid image bounds or padding")
        outside = [a for a in self.memory if not start <= a < end]
        if outside:
            raise AssemblyError(f"emitted address ${outside[0]:04X} lies outside image bounds")
        return bytes(self.memory.get(a, fill) for a in range(start, end))

    def logisim(self, start=None, end=None, fill=0) -> str:
        data = self.binary(start, end, fill)
        return "v2.0 raw\n" + "\n".join(" ".join(f"{b:02x}" for b in data[i:i+16])
                                           for i in range(0, len(data), 16)) + "\n"

    def woz(self, entry=None) -> str:
        addresses = sorted(self.memory)
        lines = []
        while addresses:
            start = addresses[0]
            row = [addresses.pop(0)]
            while addresses and addresses[0] == row[-1] + 1 and len(row) < 16:
                row.append(addresses.pop(0))
            lines.append(f"{start:04X}: " + " ".join(f"{self.memory[a]:02X}" for a in row))
        if entry is not None:
            if not 0 <= entry <= 65535:
                raise AssemblyError("entry point out of range")
            lines.append(f"{entry:04X}R")
        return "\n".join(lines) + "\n"


def assemble(source: str) -> Assembly:
    symbols, names, records = {}, set(), []
    pc = 0
    for number, original in enumerate(source.splitlines(), 1):
        try:
            line = split_fields(original, ";")[0].strip()
            if not line:
                continue
            match = re.match(r"^([A-Za-z_][A-Za-z_0-9]*):", line)
            if match:
                label = match[1].upper()
                if label in names:
                    raise AssemblyError(f"duplicate symbol {label}")
                names.add(label)
                symbols[label] = pc
                line = line[match.end():].strip()
                if not line:
                    continue
            match = re.fullmatch(r"([A-Za-z_][A-Za-z_0-9]*)\s*=\s*(.+)", line)
            if match:
                label = match[1].upper()
                if label in names:
                    raise AssemblyError(f"duplicate symbol {label}")
                names.add(label)
                # Constants must resolve where declared: predictable layout.
                symbols[label] = expression(match[2], symbols, pc)
                continue
            command, _, operand = line.partition(" ")
            if "\t" in command:
                command, operand = re.split(r"\s+", line, maxsplit=1)
            command = command.upper()
            if command == ".ORG":
                pc = expression(operand, symbols, pc)
                if not 0 <= pc <= 65535:
                    raise AssemblyError("origin outside 16-bit address space")
                continue
            if command in (".BYTE", ".WORD", ".ASCII"):
                fields = split_fields(operand)
                if not operand:
                    raise AssemblyError("empty data directive")
                items = []
                for field in fields:
                    if field.startswith('"'):
                        try:
                            value = ast.literal_eval(field)
                            if not isinstance(value, str):
                                raise ValueError()
                            data = value.encode("ascii")
                        except (SyntaxError, ValueError, UnicodeEncodeError) as exc:
                            raise AssemblyError("invalid ASCII string") from exc
                        if command == ".WORD":
                            raise AssemblyError("strings require .byte or .ascii")
                        items.extend(("literal", b) for b in data)
                    else:
                        if command == ".ASCII":
                            raise AssemblyError(".ascii requires quoted strings")
                        items.append(("word" if command == ".WORD" else "byte", field))
                size = sum(2 if kind == "word" else 1 for kind, _ in items)
                records.append((number, original, pc, "data", items))
            else:
                if not any(name == command for name, _ in OPCODES):
                    raise AssemblyError(f"unknown instruction/directive {command}")
                mode, expr = addressing(command, operand, symbols, pc)
                if (command, mode) not in OPCODES:
                    raise AssemblyError(f"{command} does not support {mode} addressing")
                size = LENGTHS[mode]
                records.append((number, original, pc, "op", (command, mode, expr)))
            if pc + size > 65536:
                raise AssemblyError("emission crosses end of address space")
            pc += size
        except AssemblyError as exc:
            raise AssemblyError(f"line {number}: {exc}") from exc

    memory, listing = {}, []
    for number, original, address, kind, value in records:
        try:
            data = []
            if kind == "data":
                for dtype, item in value:
                    n = item if dtype == "literal" else expression(item, symbols, address + len(data))
                    limit = 65535 if dtype == "word" else 255
                    if not 0 <= n <= limit:
                        raise AssemblyError(f"data value {n} outside 0..{limit}")
                    data.append(n & 255)
                    if dtype == "word":
                        data.append(n >> 8)
            else:
                name, mode, expr = value
                data = [OPCODES[(name, mode)]]
                if LENGTHS[mode] > 1:
                    n = expression(expr, symbols, address)
                    if mode == "rel":
                        if not 0 <= n <= 65535:
                            raise AssemblyError("branch target outside address space")
                        delta = (n - (address + 2)) & 65535
                        if not (delta <= 127 or delta >= 65408):
                            raise AssemblyError("relative branch outside -128..127")
                        data.append(delta & 255)
                    else:
                        limit = 65535 if LENGTHS[mode] == 3 else 255
                        if not 0 <= n <= limit:
                            raise AssemblyError(f"operand {n} outside 0..{limit}")
                        data.append(n & 255)
                        if LENGTHS[mode] == 3:
                            data.append(n >> 8)
            for offset, byte in enumerate(data):
                where = address + offset
                if where in memory:
                    raise AssemblyError(f"overlapping output at ${where:04X}")
                memory[where] = byte
            hexes = " ".join(f"{b:02X}" for b in data)
            listing.append(f"{address:04X}  {hexes:<24} {number:4}  {original}")
        except AssemblyError as exc:
            raise AssemblyError(f"line {number}: {exc}") from exc
    if not memory:
        raise AssemblyError("source emits no bytes")
    return Assembly(memory, symbols, listing)


def write_outputs(assembly, prefix: Path, start=None, end=None, entry=None, source=None, fill=0):
    start = min(assembly.memory) if start is None else start
    end = max(assembly.memory) + 1 if end is None else end
    data = assembly.binary(start, end, fill)
    prefix.parent.mkdir(parents=True, exist_ok=True)
    Path(str(prefix) + ".bin").write_bytes(data)
    Path(str(prefix) + ".hex").write_text(assembly.logisim(start, end, fill))
    Path(str(prefix) + ".lst").write_text("\n".join(assembly.listing) + "\n")
    Path(str(prefix) + ".symbols.json").write_text(json.dumps(assembly.symbols, indent=2, sort_keys=True) + "\n")
    Path(str(prefix) + ".mon").write_text(assembly.woz(entry))
    manifest = {"architecture": "NMOS 6502 documented opcodes", "origin": start,
                "end_exclusive": end, "entry": entry, "size": len(data),
                "emitted_bytes": len(assembly.memory), "padding": fill,
                "sha256": hashlib.sha256(data).hexdigest(),
                "format": "v2.0 raw, 8-bit words", "source": source}
    Path(str(prefix) + ".manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", "-o", type=Path, required=True, help="output prefix (without extension)")
    parser.add_argument("--start", type=lambda v: int(v, 0))
    parser.add_argument("--end", type=lambda v: int(v, 0), help="exclusive end address")
    parser.add_argument("--entry", help="symbol or integer entry point; append monitor run command")
    parser.add_argument("--fill", type=lambda v: int(v, 0), default=0, help="padding byte (default 0)")
    args = parser.parse_args()
    try:
        result = assemble(args.source.read_text())
        entry = expression(args.entry, result.symbols) if args.entry else None
        write_outputs(result, args.output, args.start, args.end, entry, str(args.source), args.fill)
    except (AssemblyError, OSError) as exc:
        parser.exit(1, f"{args.source}: {exc}\n")
    print(f"Assembled {len(result.memory)} bytes; outputs: {args.output}.*")


if __name__ == "__main__":
    main()
