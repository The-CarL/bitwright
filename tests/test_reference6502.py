"""CPU arithmetic/stack/addressing and firmware execution with real encoded bytes."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from asm6502 import assemble
from reference6502 import Apple1Machine, CPU6502, IllegalOpcode, B, C, D, I, N, U, V, Z
from test_6502_differential import Case, compare_output


class ArithmeticTests(unittest.TestCase):
    def test_exhaustive_binary_add_subtract_flags(self):
        cpu = CPU6502()
        for a in range(256):
            for value in range(256):
                sa = a if a < 128 else a - 256
                sb = value if value < 128 else value - 256
                for carry in (0, 1):
                    cpu.a, cpu.p = a, U | carry
                    cpu.adc(value)
                    result = a + value + carry
                    signed = sa + sb + carry
                    expected = ((C if result > 255 else 0) | (Z if result & 255 == 0 else 0)
                                | (N if result & 128 else 0) | (V if not -128 <= signed <= 127 else 0))
                    self.assertEqual((cpu.a, cpu.p & (C|Z|N|V)), (result & 255, expected))
                    cpu.a, cpu.p = a, U | carry
                    cpu.sbc(value)
                    result = a - value - 1 + carry
                    signed = sa - sb - 1 + carry
                    expected = ((C if result >= 0 else 0) | (Z if result & 255 == 0 else 0)
                                | (N if result & 128 else 0) | (V if not -128 <= signed <= 127 else 0))
                    self.assertEqual((cpu.a, cpu.p & (C|Z|N|V)), (result & 255, expected))

    def test_exhaustive_valid_bcd_results_and_carry(self):
        cpu = CPU6502()
        bcd = lambda n: (n // 10) * 16 + n % 10
        for left in range(100):
            for right in range(100):
                for carry in (0, 1):
                    cpu.a, cpu.p = bcd(left), U | D | carry
                    cpu.adc(bcd(right))
                    answer = left + right + carry
                    self.assertEqual((cpu.a, bool(cpu.p & C)), (bcd(answer % 100), answer >= 100))
                    cpu.a, cpu.p = bcd(left), U | D | carry
                    cpu.sbc(bcd(right))
                    answer = left - right - 1 + carry
                    self.assertEqual((cpu.a, bool(cpu.p & C)), (bcd(answer % 100), answer >= 0))

    def test_nmos_decimal_flags_are_pre_adjust(self):
        cpu = CPU6502()
        cpu.a, cpu.p = 0x50, U | D
        cpu.adc(0x50)
        self.assertEqual(cpu.a, 0)
        self.assertEqual(cpu.p & (C|N|V|Z), C|N|V)  # Result zero, NMOS Z remains clear.
        cpu.a, cpu.p = 0x00, U | D | C
        cpu.sbc(0x01)
        self.assertEqual((cpu.a, cpu.p & (C|N|V|Z)), (0x99, N))


class CPUExecutionTests(unittest.TestCase):
    def cpu(self, source):
        assembly = assemble(".org $0300\n" + source)
        cpu = CPU6502()
        for address, value in assembly.memory.items():
            cpu.memory[address] = value
        cpu.pc, cpu.sp = 0x300, 255
        return cpu, assembly

    def test_nested_calls_stack_order_and_wrap(self):
        cpu, asm = self.cpu("JSR outer\ndone: NOP\nouter: JSR inner\nRTS\ninner: LDA #42\nRTS")
        cpu.run(20, lambda c: c.pc == asm.symbols["DONE"])
        self.assertEqual((cpu.a, cpu.sp), (42, 255))
        self.assertEqual(cpu.writes[:2], [(0x1FF, 3), (0x1FE, 2)])
        cpu.sp = 0
        cpu.push(0xAB)
        self.assertEqual(cpu.sp, 255)
        self.assertEqual(cpu.pop(), 0xAB)

    def test_zp_pointer_and_index_wrap_and_jmp_bug(self):
        cpu, _ = self.cpu("LDX #1\nLDA ($FE,X)\nLDY #2\nLDA ($FF),Y\nJMP ($12FF)")
        cpu.memory[255], cpu.memory[0] = 0xFF, 0x04
        cpu.memory[0x4FF], cpu.memory[0x501] = 0x42, 0xA5
        cpu.memory[0x12FF], cpu.memory[0x1200], cpu.memory[0x1300] = 0x34, 0x56, 0xAB
        cpu.step(); cpu.step()
        self.assertEqual(cpu.a, 0x42)
        cpu.step(); cpu.step()
        self.assertEqual(cpu.a, 0xA5)
        cpu.step()
        self.assertEqual(cpu.pc, 0x5634)

    def test_brk_rti_and_status_stack_bit(self):
        cpu, _ = self.cpu("BRK\n.byte $EA\nNOP")
        cpu.memory[0xFFFE:0x10000] = bytes([0, 4])
        cpu.memory[0x400] = 0x40  # RTI
        cpu.p = U | C | D
        cpu.step()
        self.assertEqual(cpu.pc, 0x400)
        self.assertEqual(cpu.writes, [(0x1FF, 3), (0x1FE, 2), (0x1FD, U|B|C|D)])
        self.assertTrue(cpu.p & I)
        cpu.step()
        self.assertEqual((cpu.pc, cpu.p, cpu.sp), (0x302, U|C|D, 255))

    def test_irq_mask_nmi_and_reset_vector(self):
        cpu = CPU6502()
        cpu.memory[0xFFFA:0x10000] = bytes([0x34, 0x12, 0x78, 0x56, 0xBC, 0x9A])
        self.assertFalse(cpu.irq())
        cpu.nmi()
        self.assertEqual(cpu.pc, 0x1234)
        cpu.p &= ~I
        self.assertTrue(cpu.irq())
        self.assertEqual(cpu.pc, 0x9ABC)
        cpu.p |= D
        cpu.reset()
        self.assertEqual(cpu.pc, 0x5678)
        self.assertTrue(cpu.p & D)  # NMOS reset does not clear decimal mode.

    def test_shifts_memory_bit_flags_and_transfers(self):
        cpu, asm = self.cpu("LDA #$81\nSTA $80\nASL $80\nROL A\nLSR A\nROR $80\nBIT $80\nTAX\nTXS\nTSX\ndone: NOP")
        cpu.run(30, lambda c: c.pc == asm.symbols["DONE"])
        self.assertEqual(cpu.memory[0x80], 0x81)
        self.assertEqual((cpu.a, cpu.x, cpu.sp), (1, 1, 1))
        self.assertFalse(cpu.p & V)

    def test_fault_and_bounded_execution(self):
        cpu, _ = self.cpu(".byte $02")
        with self.assertRaises(IllegalOpcode):
            cpu.step()
        cpu, _ = self.cpu("loop: JMP loop")
        with self.assertRaises(TimeoutError):
            cpu.run(5)


class FirmwareTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rom = assemble((ROOT / "software/monitor/monitor.asm").read_text())

    def ready(self, machine, limit=200000):
        machine.cpu.run(limit, lambda c: not machine.input and c.pc == self.rom.symbols["GETC"])

    def test_boot_memory_deposit_examine_range_and_invalid(self):
        m = Apple1Machine(self.rom)
        self.ready(m)
        self.assertTrue(m.transcript.startswith("BITWRIGHT 6502\r"))
        m.feed("0300: 12 34 AB\n0300.0302\n0300\nF000: 00\n0300: 100\n03000\n")
        self.ready(m)
        self.assertEqual(m.memory[0x300:0x303], bytes([0x12, 0x34, 0xAB]))
        self.assertIn("0300: 12\r0301: 34\r0302: AB\r", m.transcript)
        self.assertEqual(m.transcript.count("?"), 3)
        self.assertEqual(m.memory[0xF000], self.rom.memory[0xF000])

    def test_load_files_through_monitor_run_two_programs_and_return(self):
        m = Apple1Machine(self.rom)
        self.ready(m)
        for demo, input_text, expected in [("hello", "K", "PRESS A KEY: K"),
                                           ("sum", "9", "SUM (HEX) = 2D"),
                                           ("memory", "", "RAM CHECKSUM (HEX) = 78")]:
            with self.subTest(demo=demo):
                program = assemble((ROOT / f"software/demos/{demo}.asm").read_text())
                m.feed(program.woz(0x300) + input_text)
                self.ready(m)
                self.assertIn(expected, m.transcript)
                for address, byte in program.memory.items():
                    self.assertEqual(m.memory[address], byte)
                self.assertTrue(m.transcript.endswith("\r\\ "))
        self.assertEqual(m.memory[0x800:0x810], bytes(range(16)))

    def test_keyboard_read_ack_status_busy_and_rom_boundaries(self):
        m = Apple1Machine(self.rom, "AB")
        self.assertEqual(m.read(0xD011), 128)
        self.assertEqual(m.read(0xD011), 128)
        self.assertEqual(m.read(0xD010), ord("A") | 128)
        self.assertEqual(m.read(0xD010), ord("B") | 128)
        self.assertEqual(m.read(0xD011), 0)
        self.assertEqual(m.read(0xD010), ord("B"))
        m.write(0xD011, 0xA7)
        self.assertEqual(m.read(0xD011), 0)
        m.write(0xD013, 0xA7)
        self.assertEqual(m.read(0xD013), 0)
        m.feed("C")
        self.assertEqual(m.read(0xD011), 128)
        m.display_busy = True
        self.assertEqual(m.read(0xD012), 128)
        with self.assertRaises(RuntimeError):
            m.write(0xD012, 65)
        for address in (0x1000, 0xF000):
            previous = m.memory[address]
            m.write(address, previous ^ 255)
            self.assertEqual(m.memory[address], previous)

    def test_backspace_escape_and_empty_line(self):
        m = Apple1Machine(self.rom)
        m.feed("\n0309\b0: AA\n0300\nGARBAGE\x1b0300\n")
        self.ready(m)
        self.assertEqual(m.memory[0x300], 0xAA)
        self.assertNotIn("?", m.transcript)

    def deposit_trace(self, machine, command):
        machine.feed(command + "\n")
        deposits = []
        for _ in range(20000):
            if not machine.input and machine.cpu.pc == self.rom.symbols["GETC"]:
                return deposits
            trace = machine.cpu.step()
            if trace["before"]["pc"] == self.rom.symbols["DEPOSIT_BYTE"]:
                deposits.extend(trace["writes"])
        self.fail("deposit command did not return to monitor")

    def test_deposits_cannot_corrupt_live_monitor_workspace(self):
        for address in (0x20, 0x27, 0x100, 0x1FF, 0x200, 0x208, 0x24F):
            with self.subTest(address=address):
                m = Apple1Machine(self.rom)
                self.ready(m)
                command = f"{address:04X}: 00 12 34"
                self.assertEqual(self.deposit_trace(m, command), [])
                self.assertEqual(m.transcript.count("?"), 1)
                # The rejected deposit must leave the parsed input intact.
                self.assertEqual(m.memory[0x200:0x201+len(command)],
                                 command.encode("ascii") + b"\x00")

    def test_deposit_crossing_reserved_region_commits_only_safe_prefix(self):
        for start, forbidden in [(0x1F, 0x20), (0xFF, 0x100), (0xFFF, 0x1000)]:
            with self.subTest(start=start):
                m = Apple1Machine(self.rom)
                self.ready(m)
                self.assertEqual(self.deposit_trace(m, f"{start:04X}: A5 5A"), [(start, 0xA5)])
                self.assertEqual(m.memory[start], 0xA5)
                self.assertEqual(m.transcript.count("?"), 1)
                if forbidden not in range(0x20, 0x28):
                    self.assertEqual(m.memory[forbidden], 0 if forbidden < 4096 else 255)
        m = Apple1Machine(self.rom)
        self.ready(m)
        for address in (0x1F, 0x28, 0xFF, 0x250, 0xFFF):
            self.assertEqual(self.deposit_trace(m, f"{address:04X}: A5"), [(address, 0xA5)])

    def test_decimal_program_return_and_hex_service_preserve_contract(self):
        m = Apple1Machine(self.rom)
        m.feed("0300: F8 4C 03 FF\n0300R\n0400: AB\n0400\n")
        self.ready(m)
        self.assertEqual(m.memory[0x400], 0xAB)
        self.assertIn("0400: AB\r", m.transcript)
        program = assemble(".org $300\nSED\nLDA #$AB\nJSR $FE03\nPHP\nPLA\nSTA $80\nJMP $FF03")
        m.feed(program.woz(0x300))
        self.ready(m)
        self.assertIn("0300R\rAB\r\\ ", m.transcript)
        self.assertTrue(m.memory[0x80] & D)
        self.assertFalse(m.cpu.p & D)

    def test_deposit_width_leading_zeros_and_overflow(self):
        m = Apple1Machine(self.rom)
        self.ready(m)
        self.assertEqual(self.deposit_trace(m, "0300: F 0A 00FF 0000"),
                         [(0x300, 15), (0x301, 10), (0x302, 255), (0x303, 0)])
        for value in ("100", "0100", "FFFF", "00000", "G"):
            with self.subTest(value=value):
                self.assertEqual(self.deposit_trace(m, "0300: " + value), [])
                self.assertEqual(m.memory[0x300], 15)

    def test_lowercase_commands_match_uppercase_display_but_program_input_is_raw(self):
        m = Apple1Machine(self.rom)
        m.feed("03a0: a9 ab 8d 00 04 4c 03 ff\n03a0r\n0400\n")
        self.ready(m)
        self.assertEqual(m.memory[0x400], 0xAB)
        self.assertIn("03A0R\r", m.transcript)
        self.assertIn("0400: AB\r", m.transcript)
        program = assemble(".org $300\nJSR $FE00\nSTA $80\nJMP $FF03")
        m.feed(program.woz(0x300) + "k")
        self.ready(m)
        self.assertEqual(m.memory[0x80], ord("k"))


class DifferentialVerifierTests(unittest.TestCase):
    def test_native_output_requires_exact_complete_cases_and_states(self):
        case = Case("nop", 0x300, 1, [(0x300, b"\xea")])
        good = "CASE\tnop\nSTATE\t769\t0\t0\t0\t253\t36\t\n"
        self.assertEqual(compare_output(good, [case]), 1)
        for output in ("", "CASE\tnop\n", good + good,
                       good.replace("769", "770"), good + "STATE\t1\t0\t0\t0\t253\t36\t\n",
                       good.replace("36\t", "36\t512:1")):
            with self.subTest(output=output), self.assertRaises(AssertionError):
                compare_output(output, [case])


if __name__ == "__main__":
    unittest.main()
