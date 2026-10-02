#!/usr/bin/env python3
"""Deterministic hardwired gate-level 6502 functional core (not cycle accurate).
No control ROM or built-in arithmetic/register/selector/processor components.
Read data samples on rising edges; external writes commit on falling edges.
"""

from __future__ import annotations
import argparse
import json
from collections import Counter
from pathlib import Path
import xml.etree.ElementTree as E
from generate_circuits import (
    attr,
    circuit,
    component,
    constant,
    gate,
    invert,
    loc,
    port,
    project,
    sink,
    source,
    text,
    tunnel,
    wire,
)

ROOT = Path(__file__).resolve().parents[1]
ROWS = {
    "ORA": {
        "imm": 9,
        "zp": 5,
        "zpx": 0x15,
        "abs": 0x0D,
        "absx": 0x1D,
        "absy": 0x19,
        "indx": 1,
        "indy": 0x11,
    },
    "AND": {
        "imm": 0x29,
        "zp": 0x25,
        "zpx": 0x35,
        "abs": 0x2D,
        "absx": 0x3D,
        "absy": 0x39,
        "indx": 0x21,
        "indy": 0x31,
    },
    "EOR": {
        "imm": 0x49,
        "zp": 0x45,
        "zpx": 0x55,
        "abs": 0x4D,
        "absx": 0x5D,
        "absy": 0x59,
        "indx": 0x41,
        "indy": 0x51,
    },
    "ADC": {
        "imm": 0x69,
        "zp": 0x65,
        "zpx": 0x75,
        "abs": 0x6D,
        "absx": 0x7D,
        "absy": 0x79,
        "indx": 0x61,
        "indy": 0x71,
    },
    "STA": {
        "zp": 0x85,
        "zpx": 0x95,
        "abs": 0x8D,
        "absx": 0x9D,
        "absy": 0x99,
        "indx": 0x81,
        "indy": 0x91,
    },
    "LDA": {
        "imm": 0xA9,
        "zp": 0xA5,
        "zpx": 0xB5,
        "abs": 0xAD,
        "absx": 0xBD,
        "absy": 0xB9,
        "indx": 0xA1,
        "indy": 0xB1,
    },
    "CMP": {
        "imm": 0xC9,
        "zp": 0xC5,
        "zpx": 0xD5,
        "abs": 0xCD,
        "absx": 0xDD,
        "absy": 0xD9,
        "indx": 0xC1,
        "indy": 0xD1,
    },
    "SBC": {
        "imm": 0xE9,
        "zp": 0xE5,
        "zpx": 0xF5,
        "abs": 0xED,
        "absx": 0xFD,
        "absy": 0xF9,
        "indx": 0xE1,
        "indy": 0xF1,
    },
    "ASL": {"acc": 0x0A, "zp": 6, "zpx": 0x16, "abs": 0x0E, "absx": 0x1E},
    "ROL": {"acc": 0x2A, "zp": 0x26, "zpx": 0x36, "abs": 0x2E, "absx": 0x3E},
    "LSR": {"acc": 0x4A, "zp": 0x46, "zpx": 0x56, "abs": 0x4E, "absx": 0x5E},
    "ROR": {"acc": 0x6A, "zp": 0x66, "zpx": 0x76, "abs": 0x6E, "absx": 0x7E},
    "STX": {"zp": 0x86, "zpy": 0x96, "abs": 0x8E},
    "STY": {"zp": 0x84, "zpx": 0x94, "abs": 0x8C},
    "LDX": {"imm": 0xA2, "zp": 0xA6, "zpy": 0xB6, "abs": 0xAE, "absy": 0xBE},
    "LDY": {"imm": 0xA0, "zp": 0xA4, "zpx": 0xB4, "abs": 0xAC, "absx": 0xBC},
    "CPX": {"imm": 0xE0, "zp": 0xE4, "abs": 0xEC},
    "CPY": {"imm": 0xC0, "zp": 0xC4, "abs": 0xCC},
    "INC": {"zp": 0xE6, "zpx": 0xF6, "abs": 0xEE, "absx": 0xFE},
    "DEC": {"zp": 0xC6, "zpx": 0xD6, "abs": 0xCE, "absx": 0xDE},
    "BIT": {"zp": 0x24, "abs": 0x2C},
    "JMP": {"abs": 0x4C, "ind": 0x6C},
    "JSR": {"abs": 0x20},
}
for name, code in [
    ("BPL", 0x10),
    ("BMI", 0x30),
    ("BVC", 0x50),
    ("BVS", 0x70),
    ("BCC", 0x90),
    ("BCS", 0xB0),
    ("BNE", 0xD0),
    ("BEQ", 0xF0),
]:
    ROWS[name] = {"rel": code}
for name, code in [
    ("BRK", 0),
    ("PHP", 8),
    ("CLC", 0x18),
    ("PLP", 0x28),
    ("SEC", 0x38),
    ("RTI", 0x40),
    ("PHA", 0x48),
    ("CLI", 0x58),
    ("RTS", 0x60),
    ("PLA", 0x68),
    ("SEI", 0x78),
    ("DEY", 0x88),
    ("TXA", 0x8A),
    ("TYA", 0x98),
    ("TXS", 0x9A),
    ("TAY", 0xA8),
    ("TAX", 0xAA),
    ("CLV", 0xB8),
    ("TSX", 0xBA),
    ("INY", 0xC8),
    ("DEX", 0xCA),
    ("CLD", 0xD8),
    ("INX", 0xE8),
    ("NOP", 0xEA),
    ("SED", 0xF8),
]:
    ROWS[name] = {"imp": code}
OPCODES = {
    code: (name, mode) for name, modes in ROWS.items() for mode, code in modes.items()
}
MNEMONICS = sorted(ROWS)
MODES = sorted({m for _, m in OPCODES.values()})
STATES = [
    "ResetLow",
    "ResetHigh",
    "Fetch",
    "Decode",
    "Operand",
    "AbsoluteHigh",
    "IndirectLow",
    "IndirectHigh",
    "ReadOperand",
    "Execute",
    "WriteOperand",
    "Push",
    "Pull",
    "CallHigh",
    "CallLow",
    "ReturnLow",
    "ReturnHigh",
    "ReturnFlags",
    "InterruptLow",
    "InterruptHigh",
    "BreakHigh",
    "BreakLow",
    "BreakFlags",
    "VectorLow",
    "VectorHigh",
    "Fault",
]
INPUTS = [("SysClock", 1), ("Reset", 1), ("DataIn", 8), ("IRQ", 1), ("NMI", 1)]
OUTPUTS = [
    ("Address", 16),
    ("DataOut", 8),
    ("Write", 1),
    ("Read", 1),
    ("Sync", 1),
    ("Fault", 1),
    ("PC", 16),
    ("A", 8),
    ("X", 8),
    ("Y", 8),
    ("SP", 8),
    ("P", 8),
    ("IR", 8),
    ("State", 8),
]


class Net:
    def __init__(self, c):
        self.c = c
        self.index = 0
        self.cache = {}
        self.serial = 0
        self.columns = 8 if c.get("name") == "Cpu6502" else 4
        constant(c, 160, 80, 0)
        tunnel(c, 160, 80, "ZERO")
        constant(c, 160, 110, 1)
        tunnel(c, 160, 110, "ONE")

    def pos(self):
        i = self.index
        self.index += 1
        return 800 + (i % self.columns) * 320, 180 + (i // self.columns) * 180

    def section(self, title):
        """Keep functional blocks apart and labelled in the native schematic."""
        self.index = (self.index // self.columns + 2) * self.columns
        text(self.c, 760, 140 + (self.index // self.columns) * 180, title)

    def fresh(self):
        self.serial += 1
        return "n" + str(self.serial)

    def named(self, a, b):
        if a == b:
            return
        x, y = self.pos()
        tunnel(self.c, x - 30, y, a, 1, "east")
        wire(self.c, (x - 30, y), (x + 30, y))
        tunnel(self.c, x + 30, y, b)

    def logic(self, kind, a, b=None):
        if kind == "NOT":
            if a in ("ZERO", "ONE"):
                return "ONE" if a == "ZERO" else "ZERO"
            key = (kind, a)
        else:
            if a == b:
                return "ZERO" if kind == "XOR" else a
            if kind == "AND":
                if "ZERO" in (a, b):
                    return "ZERO"
                if a == "ONE":
                    return b
                if b == "ONE":
                    return a
            if kind == "OR":
                if "ONE" in (a, b):
                    return "ONE"
                if a == "ZERO":
                    return b
                if b == "ZERO":
                    return a
            if kind == "XOR":
                if a == "ZERO":
                    return b
                if b == "ZERO":
                    return a
                if a == "ONE":
                    return self.NOT(b)
                if b == "ONE":
                    return self.NOT(a)
            key = (kind, *sorted((a, b)))
        if key in self.cache:
            return self.cache[key]
        out = self.fresh()
        x, y = self.pos()
        if kind == "NOT":
            invert(self.c, x, y, a, out)
        else:
            gate(self.c, kind, x, y, [a, b], out)
        self.cache[key] = out
        return out

    def NOT(self, a):
        return self.logic("NOT", a)

    def AND(self, *args):
        out = "ONE"
        for b in args:
            out = self.logic("AND", out, b)
        return out

    def OR(self, *args):
        out = "ZERO"
        for b in args:
            out = self.logic("OR", out, b)
        return out

    def XOR(self, a, b):
        return self.logic("XOR", a, b)

    # Wide masks are parallel Boolean gates, not built-in selection/arithmetic.
    def vector_gate(self, kind, a, b):
        key = ("word", kind, tuple(a), tuple(b))
        if key in self.cache:
            return self.cache[key]
        aa = self.join(a)
        bb = self.join(b)
        out = self.fresh()
        x, y = self.pos()
        gate(self.c, kind, x, y, [aa, bb], out, len(a))
        result = self.split(out, len(a))
        self.cache[key] = result
        return result

    def mux(self, s, a, b):
        if len(a) < 4:
            return [
                self.OR(self.AND(s, x), self.AND(self.NOT(s), y)) for x, y in zip(a, b)
            ]
        return self.choose([(s, a), (self.NOT(s), b)], len(a))

    def choose(self, choices, width):
        if width < 4:
            return [
                self.OR(*(self.AND(s, v[i]) for s, v in choices)) for i in range(width)
            ]
        values = []
        for select, value in choices:
            if select == "ZERO" or all(bit == "ZERO" for bit in value):
                continue
            values.append(
                value
                if select == "ONE"
                else self.vector_gate("AND", value, [select] * width)
            )
        if not values:
            return ["ZERO"] * width
        while len(values) > 1:
            values = [
                self.vector_gate("OR", values[i], values[i + 1])
                if i + 1 < len(values)
                else values[i]
                for i in range(0, len(values), 2)
            ]
        return values[0]

    def eq(self, a, n):
        return self.AND(*(v if n & (1 << i) else self.NOT(v) for i, v in enumerate(a)))

    def zero(self, a):
        return self.NOT(self.OR(*a))

    def add(self, a, b, carry="ZERO"):
        out = []
        for aa, bb in zip(a, b):
            x, y = self.pos()
            v = self.fresh()
            co = self.fresh()
            instantiate(
                self.c,
                "FullAdder",
                x,
                y,
                [("A", aa, 1), ("B", bb, 1), ("CarryIn", carry, 1)],
                [("Sum", v, 1), ("CarryOut", co, 1)],
            )
            out.append(v)
            carry = co
        return out, carry

    def split(self, name, width):
        if width == 1:
            return [name]
        x, y = self.pos()
        self.index += self.columns * ((width * 10) // 180)
        tunnel(self.c, x, y, name, width, "east")
        component(
            self.c,
            0,
            "Splitter",
            x,
            y,
            incoming=width,
            fanout=width,
            appear="right",
            facing="east",
            spacing=1,
        )
        out = []
        for i in range(width):
            label = name + "_" + str(i)
            out.append(label)
            wire(self.c, (x + 20, y + 10 + 10 * i), (x + 70, y + 10 + 10 * i))
            tunnel(self.c, x + 70, y + 10 + 10 * i, label)
        return out

    def join(self, bits, name=None):
        name = name or self.fresh()
        if len(bits) == 1:
            self.named(bits[0], name)
            return name
        x, y = self.pos()
        self.index += self.columns * ((len(bits) * 10) // 180)
        tunnel(self.c, x, y, name, len(bits), "east")
        component(
            self.c,
            0,
            "Splitter",
            x,
            y,
            incoming=len(bits),
            fanout=len(bits),
            appear="right",
            facing="east",
            spacing=1,
        )
        for i, label in enumerate(bits):
            wire(self.c, (x + 20, y + 10 + 10 * i), (x + 70, y + 10 + 10 * i))
            tunnel(self.c, x + 70, y + 10 + 10 * i, label)
        return name

    def reg(self, name, bits, enable="ONE", reset_value=0):
        x, y = self.pos()
        width = len(bits)
        din = self.join(bits)
        instantiate(
            self.c,
            "Register" + str(width) + "R" + str(reset_value),
            x,
            y,
            [
                ("Data", din, width),
                ("Enable", enable, 1),
                ("SysClock", "SysClock", 1),
                ("Reset", "Reset", 1),
            ],
            [("Q", name, width)],
        )


def C(value, n=8):
    return ["ONE" if value & (1 << i) else "ZERO" for i in range(n)]


def appearance(c, ins, outs):
    attr(c, appearance="custom")
    a = E.SubElement(c, "appear")
    h = max(len(ins), len(outs)) * 30 + 40
    E.SubElement(
        a,
        "rect",
        x="0",
        y="0",
        width="160",
        height=str(h),
        fill="#ffffff",
        stroke="#000000",
    )
    for side, ports in [("in", ins), ("out", outs)]:
        for i, (name, w) in enumerate(ports):
            px = 100 if side == "in" else 380
            py = 160 + 50 * i
            (source if side == "in" else sink)(c, px, py, name, w)
            yy = 30 + 30 * i
            xx = 0 if side == "in" else 160
            E.SubElement(
                a,
                "circ-port",
                x=str(xx - 4),
                y=str(yy - 4),
                width="8",
                height="8",
                dir=side,
                pin=f"{px},{py}",
            )
            t = E.SubElement(
                a,
                "text",
                x="8" if side == "in" else "152",
                y=str(yy - 6),
                fill="#000000",
                **{
                    "font-family": "SansSerif",
                    "font-size": "10",
                    "text-anchor": "start" if side == "in" else "end",
                },
            )
            t.text = name
    title = E.SubElement(
        a,
        "text",
        x="80",
        y=str(h - 12),
        fill="#000000",
        **{
            "font-family": "SansSerif",
            "font-size": "11",
            "font-weight": "bold",
            "text-anchor": "middle",
        },
    )
    title.text = c.get("name")
    E.SubElement(a, "circ-anchor", x="160", y="30", facing="east")


def instantiate(c, name, x, y, ins, outs):
    E.SubElement(c, "comp", name=name, loc=loc(x, y))
    for i, (_, sig, w) in enumerate(ins):
        port(c, x - 160, y + 30 * i, sig, w)
    for i, (_, sig, w) in enumerate(outs):
        port(c, x, y + 30 * i, sig, w, "right")


def leaves(p):
    c = circuit(p, "GateLatch")
    appearance(c, [("Data", 1), ("Enable", 1), ("Reset", 1)], [("Q", 1)])
    n = Net(c)
    text(
        c,
        800,
        40,
        "Gate latch: cross-coupled feedback; Reset dominates Data and Enable.",
    )
    setbit = n.AND("Enable", "Data", n.NOT("Reset"))
    resetbit = n.OR("Reset", n.AND("Enable", n.NOT("Data")))
    n.named(n.NOT(n.OR(resetbit, "Qbar")), "Q")
    n.named(n.NOT(n.OR(setbit, "Q")), "Qbar")
    c = circuit(p, "GateDff")
    appearance(c, [("Data", 1), ("SysClock", 1), ("Reset", 1)], [("Q", 1)])
    n = Net(c)
    text(
        c,
        800,
        40,
        "Gate DFF: transparent-low master and transparent-high slave; rising-edge capture.",
    )

    # Keep the named flip-flop abstraction but share its reset inversion and
    # wire the two gate latches directly, avoiding simulator boundary events.
    def latch(d, e, q):
        qb = n.fresh()
        st = n.AND(e, d, n.NOT("Reset"))
        rt = n.OR("Reset", n.AND(e, n.NOT(d)))
        n.named(n.NOT(n.OR(rt, qb)), q)
        n.named(n.NOT(n.OR(st, q)), qb)

    latch("Data", n.NOT("SysClock"), "Master")
    latch("Master", "SysClock", "Q")
    c = circuit(p, "FullAdder")
    appearance(c, [("A", 1), ("B", 1), ("CarryIn", 1)], [("Sum", 1), ("CarryOut", 1)])
    n = Net(c)
    v = n.XOR("A", "B")
    n.named(n.XOR(v, "CarryIn"), "Sum")
    n.named(n.OR(n.AND("A", "B"), n.AND(v, "CarryIn")), "CarryOut")
    for width, rv in [(1, 0), (8, 0), (8, 0xFD), (8, 0x24), (16, 0)]:
        c = circuit(p, "Register" + str(width) + "R" + str(rv))
        appearance(
            c,
            [("Data", width), ("Enable", 1), ("SysClock", 1), ("Reset", 1)],
            [("Q", width)],
        )
        n = Net(c)
        data = n.split("Data", width)
        out = []
        bank_clock = "SysClock"
        # Latch Enable only while the source clock is low. A changing enable
        # during the high phase cannot create an extra register capture edge.
        low = n.NOT("SysClock")
        x, y = n.pos()
        instantiate(
            c,
            "GateLatch",
            x,
            y,
            [("Data", "Enable", 1), ("Enable", low, 1), ("Reset", "Reset", 1)],
            [("Q", "ClockEnable", 1)],
        )
        bank_clock = n.AND("SysClock", "ClockEnable")
        for bit, dd in enumerate(data):
            raw = "raw" + str(bit)
            v = n.NOT(raw) if rv & (1 << bit) else raw
            dd = n.NOT(dd) if rv & (1 << bit) else dd
            x, y = n.pos()
            instantiate(
                c,
                "GateDff",
                x,
                y,
                [("Data", dd, 1), ("SysClock", bank_clock, 1), ("Reset", "Reset", 1)],
                [("Q", raw, 1)],
            )
            out.append(v)
        n.join(out, "Q")


def decode_signals(n):
    mn = dict(zip(MNEMONICS, n.split("Mnemonics", len(MNEMONICS))))
    md = dict(zip(MODES, n.split("AddressModes", len(MODES))))
    return (
        lambda *names: n.OR(*(mn[k] for k in names)),
        lambda *names: n.OR(*(md[k] for k in names)),
        n.OR(*mn.values()),
    )


def decoder(p):
    c = circuit(p, "InstructionDecode")
    appearance(
        c, [("IR", 8)], [("Mnemonics", len(MNEMONICS)), ("AddressModes", len(MODES))]
    )
    n = Net(c)
    ir = n.split("IR", 8)
    decoded = {v: n.eq(ir, v) for v in OPCODES}
    n.join(
        [
            n.OR(*(decoded[v] for v, (mn, m) in OPCODES.items() if mn == name))
            for name in MNEMONICS
        ],
        "Mnemonics",
    )
    n.join(
        [
            n.OR(*(decoded[v] for v, (mn, m) in OPCODES.items() if m == mode))
            for mode in MODES
        ],
        "AddressModes",
    )
    text(
        c,
        800,
        40,
        "Hardwired instruction decoder: no ROM; one decoded mnemonic and one addressing mode.",
    )
    for offset in range(0, len(MNEMONICS), 7):
        labels = ", ".join(
            f"{i}={MNEMONICS[i]}"
            for i in range(offset, min(offset + 7, len(MNEMONICS)))
        )
        text(c, 50, 400 + 26 * (offset // 7), labels)
    for offset in range(0, len(MODES), 5):
        labels = ", ".join(
            f"{i}={MODES[i]}" for i in range(offset, min(offset + 5, len(MODES)))
        )
        text(c, 50, 700 + 26 * (offset // 5), labels)


def alu(p):
    c = circuit(p, "Alu6502")
    appearance(
        c,
        [(k, 8) for k in ("A", "B", "X", "Y", "SP", "P")]
        + [("Mnemonics", len(MNEMONICS)), ("AddressModes", len(MODES))],
        [("Result", 8), ("NextP", 8)],
    )
    n = Net(c)
    A, B, X, Y, SP, P = [n.split(k, 8) for k in ("A", "B", "X", "Y", "SP", "P")]
    cls, mode, _ = decode_signals(n)
    text(
        c,
        800,
        40,
        "Gate-built 6502 ALU and flags: ripple add/subtract, Boolean/shift, increment, BCD corrections.",
    )
    n.section("Binary add / subtract / compare")
    left = n.choose(
        [(cls("CPX"), X), (cls("CPY"), Y), (n.NOT(cls("CPX", "CPY")), A)], 8
    )
    subtract = cls("SBC", "CMP", "CPX", "CPY")
    right = [n.XOR(v, subtract) for v in B]
    carry = n.OR(n.AND(cls("ADC", "SBC"), P[0]), cls("CMP", "CPX", "CPY"))
    binary, bc = n.add(left, right, carry)
    # Decimal datapath: two 4-bit adders, explicit decimal carry and corrections.
    # NMOS ADC Z uses binary sum; N/V use the pre-high-correction result.
    # NMOS SBC N/Z/V/C use the binary subtractor result.
    n.section("Decimal nibble carry and correction")
    low, lowcarry = n.add(A[:4], B[:4], P[0])
    lowfix = n.OR(lowcarry, n.AND(low[3], n.OR(low[2], low[1])))
    fixedlow, _ = n.add(low, C(6, 4))
    lowdecimal = n.mux(lowfix, fixedlow, low)
    high, highcarry = n.add(A[4:], B[4:], lowfix)
    highfix = n.OR(highcarry, n.AND(high[3], n.OR(high[2], high[1])))
    fixedhigh, _ = n.add(high, C(6, 4))
    adcdecimal = lowdecimal + n.mux(highfix, fixedhigh, high)
    sublow, subcarry = n.add(A[:4], [n.NOT(v) for v in B[:4]], P[0])
    sublowfix, _ = n.add(sublow, C(10, 4))
    subhigh, subhighcarry = n.add(A[4:], [n.NOT(v) for v in B[4:]], subcarry)
    subhighfix, _ = n.add(subhigh, C(10, 4))
    sbcdecimal = n.mux(subcarry, sublow, sublowfix) + n.mux(
        subhighcarry, subhigh, subhighfix
    )
    decimalresult = n.mux(cls("ADC"), adcdecimal, sbcdecimal)
    arithmeticresult = n.mux(n.AND(P[3], cls("ADC", "SBC")), decimalresult, binary)
    n.section("Shifts, rotates, Boolean logic and increments")
    shiftin = n.mux(mode("acc"), A, B)
    ash = ["ZERO"] + shiftin[:7]
    rol = [P[0]] + shiftin[:7]
    lsr = shiftin[1:] + ["ZERO"]
    ror = shiftin[1:] + [P[0]]
    incdecinput = n.choose(
        [(cls("INX", "DEX"), X), (cls("INY", "DEY"), Y), (cls("INC", "DEC"), B)], 8
    )
    dec = cls("DEX", "DEY", "DEC")
    delta = n.mux(dec, C(255), C(1))
    incdec, _ = n.add(incdecinput, delta)
    andres = [n.AND(a, b) for a, b in zip(A, B)]
    orres = [n.OR(a, b) for a, b in zip(A, B)]
    xorres = [n.XOR(a, b) for a, b in zip(A, B)]
    result = n.choose(
        [
            (cls("LDA", "LDX", "LDY"), B),
            (cls("ADC", "SBC", "CMP", "CPX", "CPY"), arithmeticresult),
            (cls("AND", "BIT"), andres),
            (cls("ORA"), orres),
            (cls("EOR"), xorres),
            (cls("ASL"), ash),
            (cls("LSR"), lsr),
            (cls("ROL"), rol),
            (cls("ROR"), ror),
            (cls("INC", "DEC", "INX", "DEX", "INY", "DEY"), incdec),
            (cls("TAX", "TAY"), A),
            (cls("TXA"), X),
            (cls("TYA"), Y),
            (cls("TSX"), SP),
        ],
        8,
    )
    arith = cls("ADC", "SBC", "CMP", "CPX", "CPY")
    shift = cls("ASL", "LSR", "ROL", "ROR")
    n.section("6502 condition flags")
    zn = cls(
        "LDA",
        "LDX",
        "LDY",
        "ADC",
        "SBC",
        "AND",
        "ORA",
        "EOR",
        "CMP",
        "CPX",
        "CPY",
        "ASL",
        "LSR",
        "ROL",
        "ROR",
        "INC",
        "DEC",
        "INX",
        "DEX",
        "INY",
        "DEY",
        "TAX",
        "TAY",
        "TXA",
        "TYA",
        "TSX",
        "BIT",
    )
    flags = P.copy()
    flags[1] = n.mux(zn, [n.zero(result)], [P[1]])[0]
    flags[7] = n.mux(zn, [n.mux(cls("BIT"), [B[7]], [result[7]])[0]], [P[7]])[0]
    cout = n.mux(
        arith, [bc], [n.mux(cls("ASL", "ROL"), [shiftin[7]], [shiftin[0]])[0]]
    )[0]
    flags[0] = n.mux(n.OR(arith, shift), [cout], [P[0]])[0]
    ov = n.AND(n.XOR(left[7], binary[7]), n.NOT(n.XOR(left[7], right[7])))
    flags[6] = n.mux(cls("ADC", "SBC"), [ov], [n.mux(cls("BIT"), [B[6]], [P[6]])[0]])[0]
    for index, setname, clearname in [
        (0, "SEC", "CLC"),
        (2, "SEI", "CLI"),
        (3, "SED", "CLD"),
    ]:
        flags[index] = n.OR(cls(setname), n.AND(n.NOT(cls(clearname)), flags[index]))
    decimalop = n.AND(P[3], cls("ADC", "SBC"))
    decimaladc = n.AND(P[3], cls("ADC"))
    flags[1] = n.mux(decimalop, [n.zero(binary)], [flags[1]])[0]
    flags[7] = n.mux(
        decimalop, [n.mux(cls("ADC"), [high[3]], [binary[7]])[0]], [flags[7]]
    )[0]
    decimaloverflow = n.AND(n.NOT(n.XOR(A[7], B[7])), n.XOR(A[7], high[3]))
    flags[6] = n.mux(decimaladc, [decimaloverflow], [flags[6]])[0]
    flags[0] = n.mux(decimaladc, [highfix], [flags[0]])[0]
    flags[6] = n.AND(flags[6], n.NOT(cls("CLV")))
    flags[4] = "ZERO"
    flags[5] = "ONE"
    n.join(result, "Result")
    n.join(flags, "NextP")


def build():
    p = project("Cpu6502")
    p[
        0
    ].text = "GENERATED by tools/generate_6502.py; edit generator, never generated XML."
    leaves(p)
    decoder(p)
    alu(p)
    c = circuit(p, "Cpu6502")
    appearance(c, INPUTS, OUTPUTS)
    n = Net(c)
    text(
        c,
        600,
        40,
        "BITWRIGHT / original NMOS 6502 instruction behavior, hardwired multi-cycle gate CPU; storage also built from gates",
    )
    text(
        c,
        600,
        70,
        "Rising edge: CPU reads / updates. Falling edge: external writes. Not cycle-accurate; unsupported opcodes fault.",
    )
    regs = {
        k: n.split(k, w)
        for k, w in [
            ("A", 8),
            ("X", 8),
            ("Y", 8),
            ("SP", 8),
            ("P", 8),
            ("PC", 16),
            ("IR", 8),
            ("State", 8),
            ("EA", 16),
            ("B", 8),
            ("TMP", 8),
            ("RES", 8),
            ("InterruptKind", 8),
            ("NmiPrevious", 1),
            ("NmiPending", 1),
        ]
    }
    A, X, Y, SP, P, PC, IR, S, EA, B, TMP, RES = [
        regs[k]
        for k in (
            "A",
            "X",
            "Y",
            "SP",
            "P",
            "PC",
            "IR",
            "State",
            "EA",
            "B",
            "TMP",
            "RES",
        )
    ]
    DI = n.split("DataIn", 8)
    x, y = n.pos()
    instantiate(
        c,
        "InstructionDecode",
        x,
        y,
        [("IR", "IR", 8)],
        [
            ("Mnemonics", "Mnemonics", len(MNEMONICS)),
            ("AddressModes", "AddressModes", len(MODES)),
        ],
    )
    cls, mode, known = decode_signals(n)
    st = {name: n.eq(S, i) for i, name in enumerate(STATES)}
    updates = {k: [] for k in regs}
    trans = []

    def put(k, cond, val):
        updates[k].append((cond, val))

    def go(cond, to):
        trans.append((cond, C(STATES.index(to))))

    def both(s, *names):
        return n.AND(st[s], cls(*names))

    def finish(cond):
        go(cond, "Fetch")

    n.section("Program counter and stack pointer arithmetic")
    pc1, _ = n.add(PC, C(1, 16))
    sp1, _ = n.add(SP, C(1))
    spm, _ = n.add(SP, C(255))
    pcm, _ = n.add(PC, C(65535, 16))
    isstore = cls("STA", "STX", "STY")
    isrmw = n.AND(cls("ASL", "LSR", "ROL", "ROR", "INC", "DEC"), n.NOT(mode("acc")))
    n.section("Reset vector, fetch and instruction dispatch")
    go(st["ResetLow"], "ResetHigh")
    put("TMP", st["ResetLow"], DI)
    go(st["ResetHigh"], "Fetch")
    put("PC", st["ResetHigh"], TMP + DI)
    nmiedge = n.AND("NMI", n.NOT(regs["NmiPrevious"][0]))
    nmirequest = n.OR(nmiedge, regs["NmiPending"][0])
    interrupt = n.AND(st["Fetch"], n.OR(nmirequest, n.AND("IRQ", n.NOT(P[2]))))
    put("NmiPrevious", "ONE", ["NMI"])
    put("NmiPending", "ONE", [n.AND(nmirequest, n.NOT(interrupt))])
    put("InterruptKind", interrupt, [nmirequest] + C(0, 7))
    go(interrupt, "BreakHigh")
    fetch = n.AND(st["Fetch"], n.NOT(interrupt))
    go(fetch, "Decode")
    put("IR", fetch, DI)
    put("PC", fetch, pc1)
    go(n.AND(st["Decode"], n.NOT(known)), "Fault")
    special = cls("PHA", "PHP", "PLA", "PLP", "RTS", "RTI", "BRK")
    go(n.AND(st["Decode"], mode("imp", "acc"), n.NOT(special)), "Execute")
    go(n.AND(st["Decode"], n.NOT(mode("imp", "acc")), known), "Operand")
    go(both("Decode", "PHA", "PHP"), "Push")
    go(both("Decode", "PLA", "PLP"), "Pull")
    go(both("Decode", "RTS"), "ReturnLow")
    go(both("Decode", "RTI"), "ReturnFlags")
    go(both("Decode", "BRK"), "BreakHigh")
    put("PC", both("Decode", "BRK"), pc1)
    put("InterruptKind", both("Decode", "BRK"), C(2))
    n.section("Addressing modes and operand reads")
    put("PC", st["Operand"], pc1)
    immediate = n.AND(st["Operand"], mode("imm", "rel"))
    put("B", immediate, DI)
    go(immediate, "Execute")
    absfirst = n.AND(st["Operand"], mode("abs", "absx", "absy", "ind"))
    put("TMP", absfirst, DI)
    go(absfirst, "AbsoluteHigh")
    zpindex = n.choose([(mode("zpx", "indx"), X), (mode("zpy"), Y)], 8)
    zpa, _ = n.add(DI, zpindex)
    zp = n.AND(st["Operand"], mode("zp", "zpx", "zpy"))
    put("EA", zp, zpa + C(0))
    go(n.AND(zp, isstore), "WriteOperand")
    go(n.AND(zp, n.NOT(isstore)), "ReadOperand")
    ptr = n.AND(st["Operand"], mode("indx", "indy"))
    put("EA", ptr, zpa + C(0))
    go(ptr, "IndirectLow")
    absindex = n.choose([(mode("absx"), X), (mode("absy"), Y)], 8)
    absa, _ = n.add(TMP + DI, absindex + C(0))
    put("EA", st["AbsoluteHigh"], absa)
    put("PC", st["AbsoluteHigh"], pc1)
    go(n.AND(st["AbsoluteHigh"], mode("ind")), "IndirectLow")
    go(n.AND(st["AbsoluteHigh"], n.NOT(mode("ind")), cls("JMP")), "Execute")
    go(both("AbsoluteHigh", "JSR"), "CallHigh")
    normalabs = n.AND(st["AbsoluteHigh"], n.NOT(mode("ind")), n.NOT(cls("JMP", "JSR")))
    go(n.AND(normalabs, isstore), "WriteOperand")
    go(n.AND(normalabs, n.NOT(isstore)), "ReadOperand")
    put("TMP", st["IndirectLow"], DI)
    go(st["IndirectLow"], "IndirectHigh")
    ea1, _ = n.add(EA[:8], C(1))
    indindex = n.choose([(mode("indy"), Y)], 8)
    inda, _ = n.add(TMP + DI, indindex + C(0))
    put("EA", st["IndirectHigh"], inda)
    go(n.AND(st["IndirectHigh"], cls("JMP")), "Execute")
    go(n.AND(st["IndirectHigh"], n.NOT(cls("JMP")), isstore), "WriteOperand")
    go(n.AND(st["IndirectHigh"], n.NOT(cls("JMP")), n.NOT(isstore)), "ReadOperand")
    put("B", st["ReadOperand"], DI)
    go(st["ReadOperand"], "Execute")
    finish(st["WriteOperand"])
    go(n.AND(st["Execute"], isrmw), "WriteOperand")
    finish(n.AND(st["Execute"], n.NOT(isrmw)))
    n.section("ALU interface and destination register enables")
    result = n.split("AluResult", 8)
    alu_flags = n.split("AluFlags", 8)
    x, y = n.pos()
    instantiate(
        c,
        "Alu6502",
        x,
        y,
        [(k, k, 8) for k in ("A", "B", "X", "Y", "SP", "P")]
        + [
            ("Mnemonics", "Mnemonics", len(MNEMONICS)),
            ("AddressModes", "AddressModes", len(MODES)),
        ],
        [("Result", "AluResult", 8), ("NextP", "AluFlags", 8)],
    )
    n.index += n.columns
    execute = st["Execute"]
    shift = cls("ASL", "LSR", "ROL", "ROR")
    put(
        "A",
        n.AND(
            execute,
            n.OR(
                cls("LDA", "ADC", "SBC", "AND", "ORA", "EOR", "TXA", "TYA"),
                n.AND(shift, mode("acc")),
            ),
        ),
        result,
    )
    put("X", n.AND(execute, cls("LDX", "TAX", "TSX", "INX", "DEX")), result)
    put("Y", n.AND(execute, cls("LDY", "TAY", "INY", "DEY")), result)
    put("SP", n.AND(execute, cls("TXS")), X)
    put("RES", n.AND(execute, isrmw), result)
    put("P", execute, alu_flags)
    n.section("Conditional branches and jumps")
    branchtaken = n.OR(
        n.AND(cls("BPL"), n.NOT(P[7])),
        n.AND(cls("BMI"), P[7]),
        n.AND(cls("BVC"), n.NOT(P[6])),
        n.AND(cls("BVS"), P[6]),
        n.AND(cls("BCC"), n.NOT(P[0])),
        n.AND(cls("BCS"), P[0]),
        n.AND(cls("BNE"), n.NOT(P[1])),
        n.AND(cls("BEQ"), P[1]),
    )
    branchaddr, _ = n.add(PC, B + [B[7]] * 8)
    put("PC", n.AND(execute, branchtaken), branchaddr)
    put("PC", n.AND(execute, cls("JMP")), EA)
    n.section("Stack, subroutines, BRK, IRQ and NMI")
    pushstates = n.OR(
        *(
            st[k]
            for k in (
                "Push",
                "CallHigh",
                "CallLow",
                "BreakHigh",
                "BreakLow",
                "BreakFlags",
            )
        )
    )
    put("SP", pushstates, spm)
    finish(st["Push"])
    go(st["CallHigh"], "CallLow")
    finish(st["CallLow"])
    put("PC", st["CallLow"], EA)
    pullstates = n.OR(
        *(
            st[k]
            for k in (
                "Pull",
                "ReturnLow",
                "ReturnHigh",
                "ReturnFlags",
                "InterruptLow",
                "InterruptHigh",
            )
        )
    )
    put("SP", pullstates, sp1)
    finish(st["Pull"])
    put("A", both("Pull", "PLA"), DI)
    pullflags = P.copy()
    pullflags[1] = n.zero(DI)
    pullflags[7] = DI[7]
    put("P", both("Pull", "PLA"), pullflags)
    loadedflags = DI.copy()
    loadedflags[4] = "ZERO"
    loadedflags[5] = "ONE"
    put("P", n.OR(both("Pull", "PLP"), st["ReturnFlags"]), loadedflags)
    put("TMP", n.OR(st["ReturnLow"], st["InterruptLow"]), DI)
    go(st["ReturnLow"], "ReturnHigh")
    returnaddr, _ = n.add(TMP + DI, C(1, 16))
    put("PC", st["ReturnHigh"], returnaddr)
    finish(st["ReturnHigh"])
    go(st["ReturnFlags"], "InterruptLow")
    go(st["InterruptLow"], "InterruptHigh")
    put("PC", st["InterruptHigh"], TMP + DI)
    finish(st["InterruptHigh"])
    go(st["BreakHigh"], "BreakLow")
    go(st["BreakLow"], "BreakFlags")
    go(st["BreakFlags"], "VectorLow")
    go(st["VectorLow"], "VectorHigh")
    put("TMP", st["VectorLow"], DI)
    put("PC", st["VectorHigh"], TMP + DI)
    finish(st["VectorHigh"])
    interruptflags = P.copy()
    interruptflags[2] = "ONE"
    put("P", st["BreakFlags"], interruptflags)
    go(st["Fault"], "Fault")
    n.section("External memory read / write bus")
    pcstates = n.OR(st["Fetch"], st["Operand"], st["AbsoluteHigh"])
    eastates = n.OR(st["ReadOperand"], st["WriteOperand"], st["IndirectLow"])
    addr = n.choose(
        [
            (st["ResetLow"], C(0xFFFC, 16)),
            (st["ResetHigh"], C(0xFFFD, 16)),
            (pcstates, PC),
            (eastates, EA),
            (st["IndirectHigh"], ea1 + EA[8:]),
            (pushstates, SP + C(1)),
            (pullstates, sp1 + C(1)),
            (
                st["VectorLow"],
                n.mux(regs["InterruptKind"][0], C(0xFFFA, 16), C(0xFFFE, 16)),
            ),
            (
                st["VectorHigh"],
                n.mux(regs["InterruptKind"][0], C(0xFFFB, 16), C(0xFFFF, 16)),
            ),
        ],
        16,
    )
    n.join(addr, "Address")
    pushedp = P.copy()
    pushedp[4] = n.OR(both("Push", "PHP"), regs["InterruptKind"][1])
    pushedp[5] = "ONE"
    writevalue = n.choose(
        [
            (n.AND(st["WriteOperand"], cls("STA")), A),
            (n.AND(st["WriteOperand"], cls("STX")), X),
            (n.AND(st["WriteOperand"], cls("STY")), Y),
            (n.AND(st["WriteOperand"], isrmw), RES),
            (both("Push", "PHA"), A),
            (n.OR(both("Push", "PHP"), st["BreakFlags"]), pushedp),
            (st["CallHigh"], pcm[8:]),
            (st["CallLow"], pcm[:8]),
            (st["BreakHigh"], PC[8:]),
            (st["BreakLow"], PC[:8]),
        ],
        8,
    )
    n.join(writevalue, "DataOut")
    n.named(n.AND(n.NOT("Reset"), n.OR(st["WriteOperand"], pushstates)), "Write")
    read = n.OR(
        pcstates,
        st["ReadOperand"],
        st["IndirectLow"],
        st["IndirectHigh"],
        pullstates,
        st["ResetLow"],
        st["ResetHigh"],
        st["VectorLow"],
        st["VectorHigh"],
    )
    n.named(n.AND(n.NOT("Reset"), read), "Read")
    n.named(n.AND(n.NOT("Reset"), st["Fetch"]), "Sync")
    n.named(st["Fault"], "Fault")
    n.section("State and register storage banks")
    updates["State"] = trans
    for name, old in regs.items():
        options = updates[name]
        en = n.OR(*(s for s, v in options))
        val = n.choose(options, len(old))
        rv = 0xFD if name == "SP" else 0x24 if name == "P" else 0
        n.reg(name, val, en, rv)
    return p


def primitive_counts(p):
    """Count instantiated leaves recursively, including gate storage feedback cells."""
    circuits = {c.get("name"): c for c in p.findall("circuit")}
    libraries = {lib.get("name"): lib.get("desc") for lib in p.findall("lib")}

    def walk(name):
        counts = Counter()
        for comp in circuits[name].findall("comp"):
            if comp.get("lib") is None:
                counts.update(walk(comp.get("name")))
            else:
                counts[libraries[comp.get("lib")] + "/" + comp.get("name")] += 1
        return counts

    return dict(sorted(walk("Cpu6502").items()))


def logical_gate_count(p):
    """Count one Boolean gate per bit lane, rather than per wide-gate symbol."""
    circuits = {c.get("name"): c for c in p.findall("circuit")}
    libraries = {lib.get("name"): lib.get("desc") for lib in p.findall("lib")}

    def walk(name):
        count = 0
        for comp in circuits[name].findall("comp"):
            if comp.get("lib") is None:
                count += walk(comp.get("name"))
            elif libraries[comp.get("lib")] == "#Gates":
                attributes = {a.get("name"): a.get("val") for a in comp.findall("a")}
                count += int(attributes.get("width", "1"))
        return count

    return walk("Cpu6502")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    p = build()
    E.indent(p, space="  ")
    data = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        + E.tostring(p, encoding="unicode")
        + "\n"
    )
    path = ROOT / "circuits/generated/cpu6502.circ"
    manifest = {
        "cpu": "NMOS 6502 functional, not cycle accurate",
        "opcodes": {
            f"{code:02X}": {"mnemonic": name, "mode": mode}
            for code, (name, mode) in sorted(OPCODES.items())
        },
        "storage": "All CPU state is built from cross-coupled gates, master/slave latches and gate-selected register banks; no built-in flip-flops or memory.",
        "primitive_counts_expanded": primitive_counts(p),
        "builtin_flip_flops": sum(
            v for k, v in primitive_counts(p).items() if k == "#Memory/D Flip-Flop"
        ),
        "logic_gate_count_expanded": logical_gate_count(p),
        "gate_component_count_expanded": sum(
            v for k, v in primitive_counts(p).items() if k.startswith("#Gates/")
        ),
        "simulation_optimizations": [
            "Register-bank clock enables use a gate latch open only during the low clock phase; no combinational clock gating.",
            "GateDff retains a named inspectable master/slave cell with direct gate wiring inside; GateLatch remains the bank-enable latch.",
            "Repeated selection masks use bitwise AND/OR gate symbols of width 4/8/16. Each lane is a Boolean gate; ripple arithmetic and storage remain one-bit gate constructions.",
        ],
        "reset": {
            "A": 0,
            "X": 0,
            "Y": 0,
            "SP": 253,
            "P": 36,
            "PC": "little-endian FFFC/FFFD vector",
        },
        "bus": {
            "read": "DataIn captured on rising SysClock; read side effects must occur on that same edge after the old data is presented.",
            "write": "Address/DataOut/Write settle after rising edge; external memory commits once on falling edge.",
            "Sync": "High in fetch state; inspect stable register values at the instruction boundary.",
        },
        "limitations": [
            "Functional NMOS documented instructions, not transistor-level or cycle-accurate NMOS bus behavior. No dummy writes; unsupported undocumented opcodes enter Fault.",
            "Reset intentionally initializes A/X/Y=0, SP=FD and P=24 every time, unlike physical NMOS reset/power-up behavior.",
            "IRQ and NMI are active-high logical requests. NMI transitions are sampled on rising SysClock and retained until an instruction boundary; sub-cycle pulses are not guaranteed.",
            "Gate storage is verified with Logisim-evolution 5.0.0 deterministic propagation. Other simulator versions/timing randomness require revalidation.",
            "Implemented opcode manifest is not a claim of exhaustive formal correctness; native smoke and independent differential results are separate evidence.",
        ],
        "decode_bits": {
            "Mnemonics": dict(enumerate(MNEMONICS)),
            "AddressModes": dict(enumerate(MODES)),
        },
        "states": dict(enumerate(STATES)),
    }
    mpath = ROOT / "circuits/generated/cpu6502-manifest.json"
    mdata = json.dumps(manifest, indent=2) + "\n"
    if args.check:
        if (
            not path.exists()
            or path.read_text() != data
            or not mpath.exists()
            or mpath.read_text() != mdata
        ):
            raise SystemExit("CPU generated artifacts differ")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
        mpath.write_text(mdata)
    print(
        f"Cpu6502: {len(OPCODES)} encodings, {len(list(p.iter('comp')))} components across {len(p.findall('circuit'))} circuits"
    )


if __name__ == "__main__":
    main()
