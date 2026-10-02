"""Assembler encoding, rejection, reproducibility, and independent table checks."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from asm6502 import AssemblyError, LENGTHS, OPCODES, assemble, expression, write_outputs
from reference6502 import DECODE


class AssemblerTests(unittest.TestCase):
    def test_all_151_encodings_agree_with_independent_decoder(self):
        self.assertEqual(len(OPCODES), 151)
        self.assertEqual({v: k for k, v in OPCODES.items()}, DECODE)
        operands = {"imp": "", "acc": "A", "imm": "#$42", "zp": "$42",
                    "zpx": "$42,X", "zpy": "$42,Y", "abs": "$2345",
                    "absx": "$2345,X", "absy": "$2345,Y", "ind": "($2345)",
                    "indx": "($42,X)", "indy": "($42),Y", "rel": "$0202"}
        for (name, mode), opcode in OPCODES.items():
            with self.subTest(name=name, mode=mode):
                data = assemble(f".org $0200\n{name} {operands[mode]}").binary()
                self.assertEqual(data[0], opcode)
                self.assertEqual(len(data), LENGTHS[mode])
                if LENGTHS[mode] == 3:
                    self.assertEqual(data[1:], bytes([0x45, 0x23]))

    def test_labels_little_endian_expressions_and_strings(self):
        result = assemble('''BASE = $0300
.org BASE
start: LDA #<message
LDX #>message
JMP end
message: .byte "A,;B", '\\n', 0
end: .word start, message+1
''')
        self.assertEqual(result.symbols["MESSAGE"], 0x307)
        self.assertEqual(result.binary()[:7], bytes([0xA9, 7, 0xA2, 3, 0x4C, 13, 3]))
        self.assertEqual(result.binary()[7:13], b"A,;B\n\x00")
        self.assertEqual(result.binary()[-4:], b"\x00\x03\x08\x03")
        self.assertEqual(expression("($20 + %11) * 2 | 1", {}), 71)
        self.assertEqual(expression("15 % 4", {}), 3)
        self.assertEqual(expression("15 % 1", {}), 0)
        self.assertEqual(expression("%1010 | %01", {}), 11)
        self.assertEqual(assemble("NOP ; programmer's comment with an unmatched \" quote").binary(), b"\xea")

    def test_stable_forward_reference_width_and_explicit_override(self):
        a = assemble("LDA value\nvalue: .byte 0")
        self.assertEqual(a.binary(), bytes([0xAD, 3, 0, 0]))
        a = assemble("LDA z:value\nvalue: .byte 0")
        self.assertEqual(a.binary(), bytes([0xA5, 2, 0]))
        self.assertEqual(assemble("LDA a:$12").binary(), b"\xad\x12\x00")

    def test_branch_boundaries_including_address_wrap(self):
        for source, offset in [(".org $0200\nBNE $0182", 128),
                               (".org $0200\nBNE $0281", 127),
                               (".org $FFFE\nBNE $0000", 0)]:
            self.assertEqual(assemble(source).binary()[-1], offset)
        for source in [".org $0200\nBNE $0181", ".org $0200\nBNE $0282"]:
            with self.assertRaisesRegex(AssemblyError, "relative branch"):
                assemble(source)

    def test_errors_reject_partial_programs(self):
        cases = {
            "undefined": "LDA missing",
            "duplicate": "x: NOP\nx: NOP",
            "overlapping": ".org $100\n.word 0\n.org $101\n.byte 1",
            "outside": "LDA #256",
            "outside zp": "LDA z:$1234",
            "outside data": ".byte -1",
            "outside word": ".word 65536",
            "unknown": "STZ $00",
            "unsupported": "STA #1",
            "end": ".org $FFFF\nLDA #1",
            "constant forward": "FUTURE = later\nlater: NOP",
            "non ascii": '.byte "é"',
            "unterminated": '.byte "hello',
            "unsafe": '.byte __import__("os")',
            "empty": ".org 0",
        }
        for case, source in cases.items():
            with self.subTest(case=case), self.assertRaises(AssemblyError):
                assemble(source)

    def test_expression_resource_limits_reject_unbounded_work(self):
        for source in [".byte " + "1+" * 300 + "1", ".byte (1 << 63) << 1",
                       ".byte $FFFFFFFFFFFFFFFF * $FFFFFFFFFFFFFFFF", ".byte " + "1" * 5000,
                       ".byte " + "<" * 2000 + "1"]:
            with self.subTest(source=source[:60]), self.assertRaises(AssemblyError):
                assemble(source)

    def test_output_bounds_sparse_padding_and_monitor_records(self):
        result = assemble(".org $0300\n.byte $A9,$41\n.org $0310\nRTS")
        self.assertEqual(result.binary(0x300, 0x320, 255)[2:16], bytes([255])*14)
        self.assertEqual(result.woz(0x300), "0300: A9 41\n0310: 60\n0300R\n")
        self.assertTrue(result.logisim().startswith("v2.0 raw\na9 41"))
        with self.assertRaises(AssemblyError):
            result.binary(0x301, 0x400)
        with tempfile.TemporaryDirectory() as folder:
            prefix = Path(folder) / "demo"
            write_outputs(result, prefix, entry=0x300, source="demo.asm")
            first = {p.name: p.read_bytes() for p in Path(folder).iterdir()}
            write_outputs(result, prefix, entry=0x300, source="demo.asm")
            self.assertEqual(first, {p.name: p.read_bytes() for p in Path(folder).iterdir()})
            manifest = json.loads(prefix.with_suffix(".manifest.json").read_text())
            self.assertEqual(manifest["origin"], 0x300)
            self.assertEqual(manifest["emitted_bytes"], 3)


if __name__ == "__main__":
    unittest.main()
