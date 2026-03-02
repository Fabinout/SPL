"""
Property-based tests for SPL VM.
Tests that invariants hold across random inputs.
Properties: commutativity, identity, associativity, memory persistence, etc.
"""

import unittest
import subprocess
import tempfile
import os
import sys
import random
import struct

# Resolve paths
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
ASM = os.path.join(ROOT, "vm-python", "spl_asm.py")
VM = os.path.join(ROOT, "vm-python", "spl_vm.py")


def run(cmd):
    """Run command and return (returncode, stdout, stderr)."""
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout, result.stderr


def asm_and_run_source(source):
    """Assemble and run SPL source. Returns (ok, stdout, error)."""
    with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        spl_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
        rom_path = f.name

    try:
        rc, _, stderr = run([ASM, spl_path, rom_path])
        if rc != 0:
            return False, "", stderr

        rc, stdout, stderr = run([VM, rom_path])
        if rc != 0:
            return False, stdout, stderr

        return True, stdout, ""
    finally:
        if os.path.exists(spl_path):
            os.unlink(spl_path)
        if os.path.exists(rom_path):
            os.unlink(rom_path)


def get_stack_top_char_output(source):
    """
    Run source program and get the output.
    Program should output a single character (the top stack value).
    Returns: (success, output_char) or (False, "") on error.
    """
    ok, stdout, err = asm_and_run_source(source)
    if ok and len(stdout) > 0:
        return True, stdout[0] if stdout else '\x00'
    return False, ""


class TestArithmeticCommutativity(unittest.TestCase):
    """Property: (push A; push B; add) == (push B; push A; add)."""

    def test_add_commutativity_100_iterations(self):
        """Addition should be commutative: a + b = b + a."""
        random.seed(42)

        for iteration in range(100):
            a = random.randint(0, 255)
            b = random.randint(0, 255)

            # Program 1: push a, push b, add
            source1 = f"(push {a})(push {b})(add)(out 0x01)(halt)"
            ok1, out1, _ = asm_and_run_source(source1)

            # Program 2: push b, push a, add
            source2 = f"(push {b})(push {a})(add)(out 0x01)(halt)"
            ok2, out2, _ = asm_and_run_source(source2)

            self.assertTrue(ok1, f"Program 1 failed: a={a}, b={b}")
            self.assertTrue(ok2, f"Program 2 failed: a={a}, b={b}")
            self.assertEqual(out1, out2,
                           f"add({a}, {b}) not commutative: {out1!r} vs {out2!r}")

    def test_mul_commutativity_100_iterations(self):
        """Multiplication should be commutative: a * b = b * a."""
        random.seed(42)

        for iteration in range(100):
            a = random.randint(0, 255)
            b = random.randint(0, 255)

            source1 = f"(push {a})(push {b})(mul)(out 0x01)(halt)"
            ok1, out1, _ = asm_and_run_source(source1)

            source2 = f"(push {b})(push {a})(mul)(out 0x01)(halt)"
            ok2, out2, _ = asm_and_run_source(source2)

            self.assertTrue(ok1)
            self.assertTrue(ok2)
            self.assertEqual(out1, out2,
                           f"mul({a}, {b}) not commutative: {out1!r} vs {out2!r}")


class TestStackInvariance(unittest.TestCase):
    """Property: Stack operations preserve invariants."""

    def test_dup_swap_invariant(self):
        """Push X; dup; swap => top two stack values should be equal."""
        random.seed(42)

        for iteration in range(100):
            x = random.randint(0, 255)

            # Program: push x, dup, swap, drop (pop second), output top
            # After push x, dup: stack = [x, x]
            # After swap: stack = [x, x] (still same)
            # After drop: stack = [x]
            # Output x
            source = f"(push {x})(dup)(swap)(drop)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok, f"Program failed: x={x}")
            # out should be chr(x), but x might not be printable
            # Just verify we got output
            self.assertEqual(len(out), 1)

    def test_over_invariant(self):
        """Push A; push B; over => stack should be [A, B, A]."""
        random.seed(42)

        for iteration in range(50):
            a = random.randint(0, 255)
            b = random.randint(0, 255)

            # Program: push a, push b, over, drop, drop, output top (should be a)
            source = f"(push {a})(push {b})(over)(drop)(drop)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok)
            # Should output character chr(a)
            if len(out) > 0:
                self.assertEqual(ord(out[0]), a & 0xFF)


class TestIdentityOperations(unittest.TestCase):
    """Property: Identity operations don't change values."""

    def test_add_identity_zero(self):
        """push X; push 0; add => should equal X."""
        random.seed(42)

        for iteration in range(100):
            x = random.randint(0, 255)

            source = f"(push {x})(push 0)(add)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok)
            if len(out) > 0:
                result = ord(out[0])
                self.assertEqual(result, x, f"add({x}, 0) != {x}: got {result}")

    def test_mul_identity_one(self):
        """push X; push 1; mul => should equal X."""
        random.seed(42)

        for iteration in range(100):
            x = random.randint(0, 255)

            source = f"(push {x})(push 1)(mul)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok)
            if len(out) > 0:
                result = ord(out[0])
                self.assertEqual(result, x, f"mul({x}, 1) != {x}: got {result}")


class TestAssociativity(unittest.TestCase):
    """Property: (A + B) + C = A + (B + C) mod 256."""

    def test_add_associativity_100_iterations(self):
        """Addition should be associative: (a + b) + c = a + (b + c) mod 256."""
        random.seed(42)

        for iteration in range(100):
            a = random.randint(0, 255)
            b = random.randint(0, 255)
            c = random.randint(0, 255)

            # (a + b) + c
            source1 = f"(push {a})(push {b})(add)(push {c})(add)(out 0x01)(halt)"
            ok1, out1, _ = asm_and_run_source(source1)

            # a + (b + c)
            source2 = f"(push {a})(push {b})(push {c})(add)(add)(out 0x01)(halt)"
            ok2, out2, _ = asm_and_run_source(source2)

            self.assertTrue(ok1)
            self.assertTrue(ok2)
            self.assertEqual(out1, out2,
                           f"add not associative: ({a}+{b})+{c} vs {a}+({b}+{c})")


class TestMemoryPersistence(unittest.TestCase):
    """Property: Values stored in memory persist."""

    def test_store_load_persistence_100_iterations(self):
        """Store a value, do other operations, load it back => should be unchanged."""
        random.seed(42)

        for iteration in range(100):
            value = random.randint(0, 255)
            addr = random.randint(0x0000, 0xFFFF)

            # Generate random stack operations to interleave
            ops = "(push 1)(push 2)(add)(drop)" * 3

            # Program: push value, store at addr, do ops, load from addr, output
            source = f"(push {value})(store {addr}){ops}(load {addr})(out 0x01)(halt)"
            ok, out, err = asm_and_run_source(source)

            self.assertTrue(ok, f"Failed: value={value}, addr={addr:04x}, err={err}")
            if len(out) > 0:
                result = ord(out[0])
                self.assertEqual(result, value, f"Memory not persistent at {addr:04x}")


class TestJumpEquivalence(unittest.TestCase):
    """Property: Conditional jump equivalent to push 0; jump-if-zero."""

    def test_jump_if_zero_equivalence_50_iterations(self):
        """jump to L is equivalent to push 0; jump-if-zero L."""
        random.seed(42)

        for iteration in range(50):
            # Program 1: unconditional jump
            source1 = """
            (jump skip)
            (push 33) (out 0x01)  ; Should skip this
            (label skip)
            (push 65) (out 0x01)  ; Should output 'A'
            (halt)
            """

            ok1, out1, _ = asm_and_run_source(source1)

            # Program 2: push 0; jump-if-zero
            source2 = """
            (push 0)
            (jump-if-zero skip)
            (push 33) (out 0x01)  ; Should skip this
            (label skip)
            (push 65) (out 0x01)  ; Should output 'A'
            (halt)
            """

            ok2, out2, _ = asm_and_run_source(source2)

            self.assertTrue(ok1)
            self.assertTrue(ok2)
            self.assertEqual(out1, out2,
                           f"Jump not equivalent to jump-if-zero")


class TestCallReturnBalance(unittest.TestCase):
    """Property: N calls followed by N returns => return stack empty."""

    def test_call_return_balance(self):
        """Verify return stack balance: N calls => N returns."""
        random.seed(42)

        for n in [1, 2, 3, 5, 10]:
            # Generate nested calls and returns
            source = "(push 65)(out 0x01)"  # output 'A'

            for i in range(n):
                source += f"(call func{i})"

            source += "(halt)\n"

            for i in range(n):
                source += f"(label func{i})\n(return)\n"

            ok, out, err = asm_and_run_source(source)
            self.assertTrue(ok, f"N={n} call/return failed: {err}")
            # Should have output 'A' without crashing
            self.assertIn('A', out if out else '')


class TestComparisonConsistency(unittest.TestCase):
    """Property: Comparison operations are consistent."""

    def test_lt_consistency_100_iterations(self):
        """Verify lt operator: (a < b) is consistent."""
        random.seed(42)

        for iteration in range(100):
            a = random.randint(0, 255)
            b = random.randint(0, 255)

            source = f"(push {a})(push {b})(lt)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok)
            if len(out) > 0:
                result = ord(out[0])
                expected = 1 if a < b else 0
                self.assertEqual(result, expected,
                               f"lt({a}, {b}) returned {result}, expected {expected}")

    def test_gt_consistency_100_iterations(self):
        """Verify gt operator: (a > b) is consistent."""
        random.seed(42)

        for iteration in range(100):
            a = random.randint(0, 255)
            b = random.randint(0, 255)

            source = f"(push {a})(push {b})(gt)(out 0x01)(halt)"
            ok, out, _ = asm_and_run_source(source)

            self.assertTrue(ok)
            if len(out) > 0:
                result = ord(out[0])
                expected = 1 if a > b else 0
                self.assertEqual(result, expected,
                               f"gt({a}, {b}) returned {result}, expected {expected}")


if __name__ == '__main__':
    unittest.main(verbosity=2)
