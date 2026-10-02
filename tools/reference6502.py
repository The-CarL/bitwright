#!/usr/bin/env python3
"""Independent instruction-level NMOS 6502 oracle, never delivered CPU logic.

Implements documented instructions and architectural memory effects. It is NOT
cycle-accurate: dummy reads/writes, interrupt sampling cycles and bus timing are
not modeled. Illegal opcodes fail loudly. Decimal arithmetic includes the NMOS
pre-adjust N/Z/V behavior rather than the later CMOS behavior. The NMOS indirect
JMP page-wrap behavior is intentional. All memory addresses wrap to 16 bits.

The explicit decoder below is separate from the assembler's encoding table;
execution does not call the circuit generator, simulator, or assembler.
"""
from __future__ import annotations

from collections import deque

C, Z, I, D, B, U, V, N = (1 << bit for bit in range(8))

# Rows are the high opcode nibble, columns the low nibble.
_DECODE = """
BRK.imp ORA.indx - - - ORA.zp ASL.zp - PHP.imp ORA.imm ASL.acc - - ORA.abs ASL.abs -
BPL.rel ORA.indy - - - ORA.zpx ASL.zpx - CLC.imp ORA.absy - - - ORA.absx ASL.absx -
JSR.abs AND.indx - - BIT.zp AND.zp ROL.zp - PLP.imp AND.imm ROL.acc - BIT.abs AND.abs ROL.abs -
BMI.rel AND.indy - - - AND.zpx ROL.zpx - SEC.imp AND.absy - - - AND.absx ROL.absx -
RTI.imp EOR.indx - - - EOR.zp LSR.zp - PHA.imp EOR.imm LSR.acc - JMP.abs EOR.abs LSR.abs -
BVC.rel EOR.indy - - - EOR.zpx LSR.zpx - CLI.imp EOR.absy - - - EOR.absx LSR.absx -
RTS.imp ADC.indx - - - ADC.zp ROR.zp - PLA.imp ADC.imm ROR.acc - JMP.ind ADC.abs ROR.abs -
BVS.rel ADC.indy - - - ADC.zpx ROR.zpx - SEI.imp ADC.absy - - - ADC.absx ROR.absx -
- STA.indx - - STY.zp STA.zp STX.zp - DEY.imp - TXA.imp - STY.abs STA.abs STX.abs -
BCC.rel STA.indy - - STY.zpx STA.zpx STX.zpy - TYA.imp STA.absy TXS.imp - - STA.absx - -
LDY.imm LDA.indx LDX.imm - LDY.zp LDA.zp LDX.zp - TAY.imp LDA.imm TAX.imp - LDY.abs LDA.abs LDX.abs -
BCS.rel LDA.indy - - LDY.zpx LDA.zpx LDX.zpy - CLV.imp LDA.absy TSX.imp - LDY.absx LDA.absx LDX.absy -
CPY.imm CMP.indx - - CPY.zp CMP.zp DEC.zp - INY.imp CMP.imm DEX.imp - CPY.abs CMP.abs DEC.abs -
BNE.rel CMP.indy - - - CMP.zpx DEC.zpx - CLD.imp CMP.absy - - - CMP.absx DEC.absx -
CPX.imm SBC.indx - - CPX.zp SBC.zp INC.zp - INX.imp SBC.imm NOP.imp - CPX.abs SBC.abs INC.abs -
BEQ.rel SBC.indy - - - SBC.zpx INC.zpx - SED.imp SBC.absy - - - SBC.absx INC.absx -
"""
DECODE = {code: tuple(entry.split(".")) for code, entry in enumerate(_DECODE.split()) if entry != "-"}
assert len(_DECODE.split()) == 256 and len(DECODE) == 151


class IllegalOpcode(RuntimeError):
    pass


class CPU6502:
    def __init__(self, memory=None, read=None, write=None):
        self.memory = bytearray(65536) if memory is None else memory
        if len(self.memory) != 65536:
            raise ValueError("reference memory must contain 65536 bytes")
        self.read_hook, self.write_hook = read, write
        self.a = self.x = self.y = 0
        self.sp, self.p, self.pc = 0xFD, U | I, 0
        self.instructions = 0
        self.writes = []

    def read(self, address):
        address &= 65535
        return (self.read_hook(address) if self.read_hook else self.memory[address]) & 255

    def write(self, address, value):
        address, value = address & 65535, value & 255
        self.writes.append((address, value))
        if self.write_hook:
            self.write_hook(address, value)
        else:
            self.memory[address] = value

    def word(self, address):
        return self.read(address) | self.read(address + 1) << 8

    def reset(self):
        self.sp = (self.sp - 3) & 255
        self.p = (self.p | I | U) & ~B
        self.pc = self.word(0xFFFC)

    def fetch(self):
        byte = self.read(self.pc)
        self.pc = (self.pc + 1) & 65535
        return byte

    def flag(self, flag, value):
        self.p = (self.p | flag) if value else (self.p & ~flag)

    def nz(self, value):
        value &= 255
        self.flag(Z, value == 0)
        self.flag(N, value & 128)
        return value

    def push(self, value):
        self.write(0x100 | self.sp, value)
        self.sp = (self.sp - 1) & 255

    def pop(self):
        self.sp = (self.sp + 1) & 255
        return self.read(0x100 | self.sp)

    def interrupt(self, vector=0xFFFE, break_flag=False):
        self.push(self.pc >> 8)
        self.push(self.pc)
        self.push((self.p | U | (B if break_flag else 0)) & (255 if break_flag else ~B))
        self.p = (self.p | I | U) & ~B
        self.pc = self.word(vector)

    def irq(self):
        if not self.p & I:
            self.interrupt()
            return True
        return False

    def nmi(self):
        self.interrupt(0xFFFA)

    def adc(self, value):
        a, carry = self.a, int(bool(self.p & C))
        binary = a + value + carry
        if self.p & D:
            low = (a & 15) + (value & 15) + carry
            if low >= 10:
                low = ((low + 6) & 15) + 16
            intermediate = (a & 240) + (value & 240) + low
            self.flag(Z, (binary & 255) == 0)
            self.flag(N, intermediate & 128)
            self.flag(V, (~(a ^ value) & (a ^ intermediate) & 128) != 0)
            if intermediate >= 160:
                intermediate += 96
            self.flag(C, intermediate > 255)
            self.a = intermediate & 255
        else:
            self.flag(C, binary > 255)
            self.flag(V, (~(a ^ value) & (a ^ binary) & 128) != 0)
            self.a = self.nz(binary)

    def sbc(self, value):
        a, borrow = self.a, 0 if self.p & C else 1
        binary = a - value - borrow
        self.flag(C, binary >= 0)
        self.flag(V, ((a ^ value) & (a ^ binary) & 128) != 0)
        self.nz(binary)
        if self.p & D:
            low = (a & 15) - (value & 15) - borrow
            high = (a >> 4) - (value >> 4)
            if low < 0:
                low -= 6
                high -= 1
            if high < 0:
                high -= 6
            self.a = ((high << 4) & 240) | (low & 15)
        else:
            self.a = binary & 255

    def address(self, mode):
        if mode in ("imp", "acc"):
            return None
        operand = self.fetch()
        if mode in ("imm", "rel"):
            return operand
        if mode == "zp":
            return operand
        if mode in ("zpx", "zpy"):
            return (operand + (self.x if mode == "zpx" else self.y)) & 255
        if mode == "indx":
            ptr = (operand + self.x) & 255
            return self.read(ptr) | self.read((ptr + 1) & 255) << 8
        if mode == "indy":
            base = self.read(operand) | self.read((operand + 1) & 255) << 8
            return (base + self.y) & 65535
        base = operand | self.fetch() << 8
        if mode == "abs":
            return base
        if mode in ("absx", "absy"):
            return (base + (self.x if mode == "absx" else self.y)) & 65535
        if mode == "ind":
            return self.read(base) | self.read((base & 0xFF00) | ((base + 1) & 255)) << 8
        raise AssertionError(mode)

    def state(self):
        return {"pc": self.pc, "a": self.a, "x": self.x, "y": self.y,
                "sp": self.sp, "p": (self.p | U) & ~B}

    def step(self):
        before, start = self.state(), len(self.writes)
        opcode = self.fetch()
        if opcode not in DECODE:
            raise IllegalOpcode(f"illegal opcode ${opcode:02X} at ${before['pc']:04X}")
        name, mode = DECODE[opcode]
        address = self.address(mode)
        if name in ("LDA", "LDX", "LDY", "ADC", "SBC", "AND", "ORA", "EOR", "CMP", "CPX", "CPY", "BIT"):
            value = address if mode == "imm" else self.read(address)
            if name.startswith("LD"):
                setattr(self, name[-1].lower(), self.nz(value))
            elif name == "ADC":
                self.adc(value)
            elif name == "SBC":
                self.sbc(value)
            elif name in ("AND", "ORA", "EOR"):
                self.a = self.nz({"AND": self.a & value, "ORA": self.a | value, "EOR": self.a ^ value}[name])
            elif name == "BIT":
                self.flag(Z, self.a & value == 0)
                self.flag(N, value & 128)
                self.flag(V, value & 64)
            else:
                register = self.a if name == "CMP" else self.x if name == "CPX" else self.y
                self.flag(C, register >= value)
                self.nz(register - value)
        elif name in ("STA", "STX", "STY"):
            self.write(address, getattr(self, name[-1].lower()))
        elif name in ("ASL", "LSR", "ROL", "ROR", "INC", "DEC"):
            value = self.a if mode == "acc" else self.read(address)
            carry = int(bool(self.p & C))
            if name in ("ASL", "ROL"):
                self.flag(C, value & 128)
                result = value << 1 | (carry if name == "ROL" else 0)
            elif name in ("LSR", "ROR"):
                self.flag(C, value & 1)
                result = value >> 1 | (carry << 7 if name == "ROR" else 0)
            else:
                result = value + (1 if name == "INC" else -1)
            result = self.nz(result)
            if mode == "acc":
                self.a = result
            else:
                self.write(address, result)
        elif mode == "rel":
            flag, wanted = {"BCC": (C, False), "BCS": (C, True), "BEQ": (Z, True),
                            "BNE": (Z, False), "BMI": (N, True), "BPL": (N, False),
                            "BVC": (V, False), "BVS": (V, True)}[name]
            if bool(self.p & flag) == wanted:
                self.pc = (self.pc + address - (256 if address & 128 else 0)) & 65535
        elif name == "JMP":
            self.pc = address
        elif name == "JSR":
            return_address = (self.pc - 1) & 65535
            self.push(return_address >> 8)
            self.push(return_address)
            self.pc = address
        elif name == "RTS":
            low = self.pop()
            self.pc = ((self.pop() << 8 | low) + 1) & 65535
        elif name == "RTI":
            self.p = (self.pop() | U) & ~B
            low = self.pop()
            self.pc = self.pop() << 8 | low
        elif name == "BRK":
            self.pc = (self.pc + 1) & 65535
            self.interrupt(break_flag=True)
        elif name in ("PHA", "PHP"):
            self.push(self.a if name == "PHA" else self.p | B | U)
        elif name == "PLA":
            self.a = self.nz(self.pop())
        elif name == "PLP":
            self.p = (self.pop() | U) & ~B
        elif name in ("INX", "INY", "DEX", "DEY"):
            register = name[-1].lower()
            setattr(self, register, self.nz(getattr(self, register) + (1 if name[0] == "I" else -1)))
        elif name in ("TAX", "TAY", "TXA", "TYA", "TSX", "TXS"):
            source, target = name[1].lower(), name[2].lower()
            source = "sp" if source == "s" else source
            target = "sp" if target == "s" else target
            value = getattr(self, source)
            setattr(self, target, value if name == "TXS" else self.nz(value))
        elif name in ("CLC", "SEC", "CLI", "SEI", "CLD", "SED", "CLV"):
            self.flag({"C": C, "I": I, "D": D, "V": V}[name[-1]], name.startswith("SE"))
        elif name != "NOP":
            raise AssertionError(name)
        self.p = (self.p | U) & ~B
        self.instructions += 1
        return {"before": before, "opcode": opcode, "after": self.state(), "writes": self.writes[start:]}

    def run(self, max_steps=100000, until=None):
        for _ in range(max_steps):
            if until is not None and until(self):
                return self.instructions
            self.step()
        if until is not None and until(self):
            return self.instructions
        raise TimeoutError(f"reference CPU exceeded {max_steps} instructions at ${self.pc:04X}")


class Apple1Machine:
    """Development fixture: 4 KiB RAM, F000 ROM and D010-D013 console contract.

    Queued characters are a scripted test source, NOT the circuit's hardware FIFO.
    Host input is consumed only by D010 reads; D011 polls never consume input.
    ROM and unmapped writes are ignored. The trace records all issued CPU writes.
    D011/D013 control writes are ignored, matching Bitwright's small circuit
    interface; this fixture does not emulate a complete historical PIA chip.
    """
    def __init__(self, rom=None, input_text=""):
        self.memory = bytearray([255]) * 65536
        self.memory[:4096] = bytes(4096)
        self.input = deque()
        self.last_key = 0
        self.output = []
        self.display_busy = False
        if rom:
            contents = rom.memory if hasattr(rom, "memory") else rom
            for address, value in contents.items():
                if not 0xF000 <= address <= 65535:
                    raise ValueError("ROM bytes must be in F000..FFFF")
                self.memory[address] = value
        self.feed(input_text)
        self.cpu = CPU6502(self.memory, self.read, self.write)
        self.cpu.reset()

    def feed(self, text):
        self.input.extend(text.replace("\n", "\r").encode("ascii"))

    @property
    def transcript(self):
        return "".join(chr(c) for c in self.output)

    def read(self, address):
        if address == 0xD010:
            if self.input:
                self.last_key = self.input.popleft()
                return self.last_key | 128
            return self.last_key
        if address == 0xD011:
            return 128 if self.input else 0
        if address == 0xD012:
            return 128 if self.display_busy else 0
        if address == 0xD013:
            return 0
        return self.memory[address]

    def write(self, address, value):
        if address < 4096:
            self.memory[address] = value
        elif address == 0xD012:
            if self.display_busy:
                raise RuntimeError("CPU wrote display while busy")
            self.output.append(value & 127)
