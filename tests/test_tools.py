"""Negative tests for the verifier: false-green results are a release blocker."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from logisim import Result, VerificationError, check_tty, check_vectors, run, validate_image
from audit import audit


def result(text, code=0, err=""):
    return Result(["fake-logisim"], code, text, err, 0)


class VectorVerificationTests(unittest.TestCase):
    def test_complete_pass(self):
        self.assertEqual(check_vectors(result("Passed: 4, Failed: 0"), 4), (4, 0))

    def test_zero_exit_does_not_mask_failure(self):
        with self.assertRaises(VerificationError):
            check_vectors(result("Passed: 3, Failed: 1"), 4)

    def test_missing_setup_empty_partial_duplicate_and_process_error_fail(self):
        for text, count, code in [("Error preparing test vector: no pin", 4, 0),
                                  ("", 4, 0), ("Passed: 0, Failed: 0", 0, 0),
                                  ("Passed: 3, Failed: 0", 4, 0),
                                  ("Passed: 4, Failed: 0\nPassed: 4, Failed: 0", 4, 0),
                                  ("Passed: 4, Failed: 0", 4, 1)]:
            with self.subTest(text=text), self.assertRaises(VerificationError):
                check_vectors(result(text, code), count)

    def test_negative_test_requires_actual_comparison_failure(self):
        self.assertEqual(check_vectors(result("Passed: 3, Failed: 1"), 4, negative=True), (3, 1))
        for text in ["Passed: 4, Failed: 0", "Error loading test vector"]:
            with self.assertRaises(VerificationError):
                check_vectors(result(text), 4, negative=True)

    def test_timeout_fails(self):
        with self.assertRaisesRegex(VerificationError, "Timed out"):
            run([sys.executable, "-c", "import time; time.sleep(10)"], timeout=0.1)


class ArtifactTests(unittest.TestCase):
    def test_tty_checks_labelled_signature_despite_layout_order(self):
        with tempfile.TemporaryDirectory() as folder:
            project = Path(folder) / "test.circ"
            for signature_y, output in [(20, "1010 0101\t1\n"), (40, "1\t1010 0101\n")]:
                project.write_text(f'''<project><circuit name="test">
                  <comp name="Pin" loc="(10,10)"><a name="output" val="true"/><a name="label" val="halt"/></comp>
                  <comp name="Pin" loc="(10,30)"><a name="output" val="true"/><a name="label" val="pass"/></comp>
                  <comp name="Pin" loc="(10,{signature_y})"><a name="output" val="true"/><a name="label" val="signature"/><a name="width" val="8"/></comp>
                </circuit></project>''')
                check_tty(result(output), project, "test", {"pass": 1, "signature": 0xa5})
                for wrong in [output.replace("1010", "xxxx"), output.replace("0101", "0100"), ""]:
                    with self.assertRaises(VerificationError):
                        check_tty(result(wrong), project, "test", {"pass": 1, "signature": 0xa5})

    def test_memory_image_validation(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "memory.hex"
            path.write_text("v2.0 raw\na5 15*00 # sixteen words\n")
            self.assertEqual(validate_image(path, words=16), 16)
            for text in ["v2.0 raw\n", "a5", "v2.0 raw\n100", "v2.0 raw\n0*ff", "v2.0 raw\nnope"]:
                path.write_text(text)
                with self.assertRaises(VerificationError):
                    validate_image(path)

    def test_audit_follows_external_library_and_rejects_hidden_register(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            main = root / "main.circ"
            child = root / "child.circ"
            main.write_text('<project source="5.0.0"><lib name="x" desc="file#child.circ"/><circuit name="main"><comp lib="x" name="child"/></circuit></project>')
            child.write_text('<project source="5.0.0"><lib name="0" desc="#Memory"/><circuit name="child"><comp lib="0" name="Register"/></circuit></project>')
            with self.assertRaisesRegex(VerificationError, "Prohibited"):
                audit([main], root)
            child.write_text(child.read_text().replace("Register", "D Flip-Flop"))
            self.assertEqual(audit([main], root)["native_files"], 2)

    def test_audit_rejects_missing_and_absolute_dependencies(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            main = root / "main.circ"
            for name in ["missing.circ", "/tmp/absolute.circ", "../outside.circ"]:
                main.write_text(f'<project source="5.0.0"><lib name="x" desc="file#{name}"/></project>')
                with self.assertRaises(VerificationError):
                    audit([main], root)

    def test_audit_rejects_unused_unapproved_or_missing_jar(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            main = root / "main.circ"
            for descriptor in ["jar#missing.jar#org.bitwright.bridge.BitwrightLibrary",
                               "jar#/tmp/absolute.jar#org.bitwright.bridge.BitwrightLibrary",
                               "jar#local.jar#org.bitwright.OtherLibrary"]:
                main.write_text(f'<project source="5.0.0"><lib name="x" desc="{descriptor}"/></project>')
                with self.assertRaises(VerificationError):
                    audit([main], root)


class TerminalBoundaryTests(unittest.TestCase):
    def test_default_denies_even_unused_existing_approved_bridge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "bridge.jar").write_bytes(b"placeholder")
            project = root / "main.circ"
            project.write_text('<project source="5.0.0"><lib name="j" desc="jar#bridge.jar#org.bitwright.bridge.BitwrightLibrary"/><circuit name="main"/></project>')
            for require in [True, False]:
                with self.assertRaisesRegex(VerificationError, "outside the default terminal target"):
                    audit([project], root, require_jars=require)
            self.assertEqual(audit([project], root, experiment=True)["native_files"], 1)

    def test_rgb_video_requires_explicit_experiment_policy(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            project = root / "main.circ"
            project.write_text('<project source="5.0.0"><lib name="i" desc="#I/O"/><circuit name="main"><comp lib="i" name="RGB Video"/></circuit></project>')
            with self.assertRaisesRegex(VerificationError, "Prohibited"):
                audit([project], root)
            self.assertEqual(audit([project], root, experiment=True)["#I/O/RGB Video"], 1)

    def test_terminal_audit_follows_unused_library_to_hidden_bridge(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "main.circ").write_text('<project source="5.0.0"><lib name="child" desc="file#child.circ"/></project>')
            (root / "child.circ").write_text('<project source="5.0.0"><lib name="j" desc="jar#bridge.jar#org.bitwright.bridge.BitwrightLibrary"/></project>')
            with self.assertRaisesRegex(VerificationError, "outside the default terminal target"):
                audit([root / "main.circ"], root)

    def test_package_allowlist_works_without_optional_files_and_excludes_them(self):
        from bw import CORE_FILES, package_files
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in CORE_FILES:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("fixture")
            initial = package_files(root)
            self.assertIn("images/memory/m0-ram.manifest.json", initial)
            for name in ["build/bitwright-bridge.jar", "bridges/build.py", "experiments/mouse-canvas/workbench.circ", "tools/java/experiments/M0PixelSmoke.java", "tools/not-approved.py"]:
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("must not ship")
            self.assertEqual(package_files(root), initial)
            self.assertFalse(any(name.endswith(".jar") or name.startswith(("bridges/", "experiments/")) for name in initial))

    def test_package_is_deterministic_and_manifest_is_verified(self):
        from bw import package_bytes, verify_package
        import io
        import zipfile
        files = {"circuits/bitwright.circ": b"native circuit", "README.md": b"terminal package"}
        first = package_bytes(files)
        self.assertEqual(first, package_bytes(dict(reversed(list(files.items())))))
        with tempfile.TemporaryDirectory() as folder:
            archive = Path(folder) / "package.zip"
            archive.write_bytes(first)
            verify_package(archive)
            with zipfile.ZipFile(io.BytesIO(first)) as source:
                members = {entry.filename: source.read(entry.filename) for entry in source.infolist()}
            members["bitwright-m0/README.md"] = b"tampered"
            with zipfile.ZipFile(archive, "w") as output:
                for name, value in members.items():
                    output.writestr(name, value)
            with self.assertRaisesRegex(VerificationError, "checksum mismatch"):
                verify_package(archive)


if __name__ == "__main__":
    unittest.main()
