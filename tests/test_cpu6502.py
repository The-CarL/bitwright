"""Structural guardrails for the gate CPU; behavior is verified by native tests."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from generate_6502 import build, primitive_counts


class GateCpuStructure(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.project = build()

    def test_cpu_has_only_gates_and_wiring_foundations(self):
        counts = primitive_counts(self.project)
        self.assertTrue(any(k.startswith("#Gates/") for k in counts))
        for name in counts:
            self.assertTrue(name.startswith(("#Gates/", "#Wiring/", "#Base/")), name)
        self.assertFalse(any(name.startswith("#Memory/") for name in counts))

    def test_no_hidden_rom_control_or_builtin_processor_in_unused_circuits(self):
        allowed = {"#Gates", "#Wiring", "#Base"}
        libraries = {
            lib.get("name"): lib.get("desc") for lib in self.project.findall("lib")
        }
        for comp in self.project.iter("comp"):
            if comp.get("lib") is not None:
                self.assertIn(libraries[comp.get("lib")], allowed)

    def test_hierarchy_exposes_storage_decode_and_alu(self):
        circuits = {c.get("name"): c for c in self.project.findall("circuit")}
        for name in (
            "GateLatch",
            "GateDff",
            "FullAdder",
            "InstructionDecode",
            "Alu6502",
            "Cpu6502",
        ):
            self.assertIn(name, circuits)
        core_children = {
            comp.get("name")
            for comp in circuits["Cpu6502"].findall("comp")
            if comp.get("lib") is None
        }
        self.assertIn("Alu6502", core_children)
        self.assertIn("InstructionDecode", core_children)
        self.assertTrue(any(name.startswith("Register") for name in core_children))


if __name__ == "__main__":
    unittest.main()
