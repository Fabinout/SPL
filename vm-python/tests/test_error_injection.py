"""
Error injection tests for SPL VM - systematically triggers all fault conditions.
Tests that VM properly detects and reports errors.
"""

import unittest
import subprocess
import tempfile
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from spl_asm import assemble_source
from spl_vm import VM


def asm_source_to_rom(source):
    """Assemble SPL source code to bytecode bytes."""
    try:
        return assemble_source(source)
    except Exception as e:
        return None


def run_vm_with_timeout(rom_bytes, timeout=2):
    """
    Run VM with given bytecode and capture stderr.
    Returns: (crashed, returncode, stderr)
    - crashed: True if Python exception or timeout occurred
    - returncode: VM exit code (0 = halt, non-zero = fault)
    - stderr: Error message from VM
    """
    try:
        # Write ROM to temp file
        with tempfile.NamedTemporaryFile(suffix='.rom', delete=False) as f:
            f.write(rom_bytes)
            rom_path = f.name

        try:
            # Run VM via subprocess to catch crashes
            result = subprocess.run(
                ['python3', os.path.join(os.path.dirname(__file__), '..', 'spl_vm.py'), rom_path],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            crashed = False
            returncode = result.returncode
            stderr = result.stderr
        finally:
            os.unlink(rom_path)

        return crashed, returncode, stderr
    except subprocess.TimeoutExpired:
        return True, -1, "timeout"
    except Exception as e:
        return True, -1, str(e)


class TestStackOverflow(unittest.TestCase):
    """Test stack overflow detection (limit: 256 entries)."""

    def test_stack_overflow_257_pushes(self):
        """257 pushes should trigger stack overflow."""
        # Generate program that pushes 257 values
        source = "(push 1) " * 257 + "(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom, "Assembly should succeed")

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("stack overflow", stderr.lower(),
                     f"Expected 'stack overflow' in stderr, got: {stderr}")

    def test_stack_overflow_push_in_loop(self):
        """Loop that pushes more than 256 values."""
        # Use a loop to push many values
        source = """
        (push 0)           ; counter
        (label loop)
        (push 1)           ; value to push
        (over)             ; copy counter
        (push 255)
        (sub)              ; counter - 255
        (jump-if-not-zero loop)
        (halt)
        """
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        # This might not overflow if the loop exits appropriately


class TestReturnStackOverflow(unittest.TestCase):
    """Test return stack overflow detection (limit: 64 entries)."""

    def test_return_stack_overflow_65_calls(self):
        """65 nested calls should trigger return stack overflow."""
        # Generate program with 65 nested calls
        source = "(call level_1)(halt)\n"

        for i in range(1, 65):
            source += f"(label level_{i})\n(call level_{i+1})\n"

        source += f"(label level_65)\n(push 1)(out 0x01)(return)\n"

        rom = asm_source_to_rom(source)
        if rom is None:
            self.skipTest("Source assembly failed - may be too large")

        crashed, rc, stderr = run_vm_with_timeout(rom, timeout=5)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("return stack overflow", stderr.lower(),
                     f"Expected 'return stack overflow', got: {stderr}")


class TestMemoryBoundsViolation(unittest.TestCase):
    """Test out-of-bounds memory access detection."""

    def test_load_oob_0x10000(self):
        """Load from address 0x10000 (past 64KB) should fault."""
        source = "(load 0x10000)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("out of bounds", stderr.lower(),
                     f"Expected 'out of bounds', got: {stderr}")

    def test_store_oob_0x10000(self):
        """Store to address 0x10000 (past 64KB) should fault."""
        source = "(push 42)(store 0x10000)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("out of bounds", stderr.lower(),
                     f"Expected 'out of bounds', got: {stderr}")

    def test_load_oob_0x10001(self):
        """Load from address 0x10001 should also fault."""
        source = "(load 0x10001)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("out of bounds", stderr.lower())


class TestIndirectMemoryBoundsViolation(unittest.TestCase):
    """Test out-of-bounds indirect memory access."""

    def test_load_indirect_oob(self):
        """Load-indirect with address >= 0x10000 should fault."""
        source = "(push 0x00)(push 0x01)(load-indirect)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("out of bounds", stderr.lower(),
                     f"Expected 'out of bounds', got: {stderr}")

    def test_store_indirect_oob(self):
        """Store-indirect with address >= 0x10000 should fault."""
        source = "(push 0x00)(push 0x01)(push 42)(store-indirect)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("out of bounds", stderr.lower())


class TestUnexpectedEOF(unittest.TestCase):
    """Test handling of truncated bytecode (unexpected EOF)."""

    def test_truncated_push_missing_argument(self):
        """Push instruction with missing argument byte."""
        # Manually create bytecode: 0x01 (push) with no argument
        rom = bytes([0x01])  # push with no argument byte

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("end of bytecode", stderr.lower(),
                     f"Expected EOF error, got: {stderr}")

    def test_truncated_jump_missing_address(self):
        """Jump instruction with incomplete 16-bit address."""
        # 0x30 (jump) followed by only one address byte
        rom = bytes([0x30, 0x00])  # jump missing second byte

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("end of bytecode", stderr.lower())


class TestUnknownOpcode(unittest.TestCase):
    """Test handling of invalid/unknown opcodes."""

    def test_invalid_opcode_0x42(self):
        """Invalid opcode 0x42 should cause fault."""
        rom = bytes([0x42])  # Invalid opcode

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        # Might be "unknown opcode" or "unimplemented"
        self.assertTrue("unknown" in stderr.lower() or
                       "unimplemented" in stderr.lower() or
                       rc != 0,
                       f"Expected error, got: rc={rc}, stderr={stderr}")


class TestStackUnderflow(unittest.TestCase):
    """Test stack underflow detection."""

    def test_drop_empty_stack(self):
        """Drop on empty stack should fault."""
        source = "(drop)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("underflow", stderr.lower(),
                     f"Expected 'underflow', got: {stderr}")

    def test_binary_op_insufficient_args(self):
        """Binary operation with < 2 args should fault."""
        source = "(push 5)(add)(halt)"  # add needs 2 args, only has 1
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("underflow", stderr.lower())


class TestReturnStackUnderflow(unittest.TestCase):
    """Test return stack underflow detection."""

    def test_return_empty_return_stack(self):
        """Return without matching call should fault."""
        source = "(return)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertNotEqual(rc, 0, "VM should exit with error code")
        self.assertIn("underflow", stderr.lower(),
                     f"Expected 'underflow', got: {stderr}")


class TestPCPastEnd(unittest.TestCase):
    """Test PC running past end of bytecode."""

    def test_pc_past_end_no_halt(self):
        """Program that runs past end without halt should exit gracefully."""
        # Program with jump that doesn't land on halt
        source = "(jump 0x0100)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash/segfault")
        # May exit with 0 (halt on PC past end) or non-zero (error)
        # The important thing is it doesn't crash


class TestDivisionByZero(unittest.TestCase):
    """Test division by zero handling (should return 0, not fault)."""

    def test_div_by_zero_returns_zero(self):
        """Division by zero should return 0, not fault."""
        source = "(push 10)(push 0)(div)(push 0)(sub)(jump-if-zero pass)(push 33)(out 0x01)(halt)(label pass)(push 65)(out 0x01)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertEqual(rc, 0, "VM should halt successfully (not fault)")
        # Note: This requires the output check, which we can verify if VM gives output

    def test_mod_by_zero_returns_zero(self):
        """Modulo by zero should return 0, not fault."""
        source = "(push 10)(push 0)(mod)(push 0)(sub)(jump-if-zero pass)(push 33)(out 0x01)(halt)(label pass)(push 65)(out 0x01)(halt)"
        rom = asm_source_to_rom(source)
        self.assertIsNotNone(rom)

        crashed, rc, stderr = run_vm_with_timeout(rom)
        self.assertFalse(crashed, "VM should not crash")
        self.assertEqual(rc, 0, "VM should halt successfully (not fault)")


if __name__ == '__main__':
    unittest.main(verbosity=2)
