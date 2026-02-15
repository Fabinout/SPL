"""
String escape sequence tests for SPL assembler.
Tests that the data pseudo-instruction correctly handles escape sequences.
"""

import unittest
import subprocess
import tempfile
import os
import sys

# Resolve paths relative to the project root
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
ASM = os.path.join(ROOT, "vm-python", "spl_asm.py")


def run(cmd):
    """Run command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=True,
    )
    return result.returncode, result.stdout, result.stderr.decode("utf-8", errors="replace")


def assemble_to_bytes(source):
    """
    Assemble SPL source and return the ROM bytecode.
    Returns None if assembly fails.
    """
    with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        spl_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
        rom_path = f.name

    try:
        rc, _, stderr = run([ASM, spl_path, rom_path])
        if rc != 0:
            return None

        with open(rom_path, 'rb') as f:
            return f.read()
    finally:
        if os.path.exists(spl_path):
            os.unlink(spl_path)
        if os.path.exists(rom_path):
            os.unlink(rom_path)


class TestStringEscapeSequences(unittest.TestCase):
    """Test string escape sequences in data pseudo-instruction."""

    def test_escape_newline(self):
        """Verify \\n escape produces 0x0A (newline)."""
        # Jump over data, then halt
        source = r'(jump after)(data msg "\n")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        # Expected bytecode:
        # 0x30 0x00 0x04: jump to 0x0004
        # 0x0A: the newline byte
        # 0x00: halt
        self.assertEqual(rom[3], 0x0A, f"Expected newline (0x0A), got {rom[3]:02x}")

    def test_escape_tab(self):
        """Verify \\t escape produces 0x09 (tab)."""
        source = r'(jump after)(data msg "\t")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        self.assertEqual(rom[3], 0x09, f"Expected tab (0x09), got {rom[3]:02x}")

    def test_escape_backslash(self):
        """Verify \\\\ escape produces 0x5C (backslash)."""
        source = r'(jump after)(data msg "\\")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        self.assertEqual(rom[3], 0x5C, f"Expected backslash (0x5C), got {rom[3]:02x}")

    def test_escape_quote(self):
        """Verify \\" escape produces 0x22 (quote)."""
        source = r'(jump after)(data msg "\"")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        self.assertEqual(rom[3], 0x22, f"Expected quote (0x22), got {rom[3]:02x}")

    def test_escape_null(self):
        """Verify \\0 escape produces 0x00 (null)."""
        source = r'(jump after)(data msg "\0")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        self.assertEqual(rom[3], 0x00, f"Expected null (0x00), got {rom[3]:02x}")

    def test_mixed_escapes(self):
        """Verify multiple escapes in one string."""
        # String: "A\nB" should produce 'A' 0x0A 'B'
        source = r'(jump after)(data msg "A\nB")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        # Expected: jump 0x30 0x00 0x05, then 'A', newline, 'B', halt 0x00
        self.assertEqual(rom[3], ord('A'), f"Expected 'A' at pos 3")
        self.assertEqual(rom[4], 0x0A, f"Expected newline at pos 4")
        self.assertEqual(rom[5], ord('B'), f"Expected 'B' at pos 5")

    def test_escaped_backslash_then_n(self):
        """Verify \\\\n produces backslash followed by 'n', not newline."""
        # This tests that we correctly distinguish "\\\n" (backslash-newline)
        # from literal "\\n" which in Python source is escaped
        # In SPL source, \\\\n should be backslash then 'n'
        source = r'(jump after)(data msg "\\n")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        # Expected: 0x5C (backslash), 0x6E ('n')
        self.assertEqual(rom[3], 0x5C, f"Expected backslash (0x5C), got {rom[3]:02x}")
        self.assertEqual(rom[4], 0x6E, f"Expected 'n' (0x6E), got {rom[4]:02x}")

    def test_all_escapes_in_sequence(self):
        """Verify all escape sequences work together."""
        # String: "\n\t\\\"\0" = newline, tab, backslash, quote, null
        source = r'(jump after)(data msg "\n\t\\\"\0")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        expected_bytes = [0x0A, 0x09, 0x5C, 0x22, 0x00]
        for i, expected in enumerate(expected_bytes):
            self.assertEqual(rom[3 + i], expected,
                           f"Byte {i}: expected {expected:02x}, got {rom[3 + i]:02x}")

    def test_data_with_numeric_bytes(self):
        """Verify numeric bytes still work (not affected by string tests)."""
        source = '(jump after)(data msg 72 101 108)(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        # Expected: 'H', 'e', 'l'
        self.assertEqual(rom[3], 72)
        self.assertEqual(rom[4], 101)
        self.assertEqual(rom[5], 108)

    def test_mixed_numeric_and_string(self):
        """Verify we can mix numeric bytes and strings in data."""
        # This tests that existing numeric data support isn't broken
        source = '(jump after)(data msg "Hi")(label after)(halt)'
        rom = assemble_to_bytes(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        # Expected: 'H', 'i'
        self.assertEqual(rom[3], ord('H'))
        self.assertEqual(rom[4], ord('i'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
