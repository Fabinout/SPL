#!/usr/bin/env python3
"""Automated test runner for the SPL Python VM.

Usage: python vm-python/tests/run_tests.py
  (run from the project root)
"""

import subprocess
import sys
import os
import tempfile

# Resolve paths relative to the project root
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
ASM = os.path.join(ROOT, "vm-python", "spl_asm.py")
VM = os.path.join(ROOT, "vm-python", "spl_vm.py")
TEST_ALL = os.path.join(ROOT, "vm-python", "tests", "test_all.spl")

# Assembler error cases: (source_text, expected_stderr_substring)
ASM_ERROR_TESTS = [
    ("(push 999)",          "out of range"),
    ("(load my-label)",     "numeric address, not a label"),
    ("(jump nowhere)",      "undefined label"),
    ("(label x)(label x)",  "duplicate label"),
    ("(bogus)",             "unknown instruction"),
    ("(data my-data)",      "at least one data"),
    ("(data 123 45)",       "must be a label"),
]

# VM runtime error cases: (source_text, expected_stderr_substring)
VM_ERROR_TESTS = [

    ("(drop)",   "stack underflow"),
    ("(return)", "return stack underflow"),
]


def run(cmd):
    result = subprocess.run(
        [sys.executable] + cmd,
        capture_output=True,
    )
    return result.returncode, result.stdout, result.stderr.decode("utf-8", errors="replace")


def asm_and_run(spl_path):
    """Assemble and run an .spl file. Returns (ok, stdout_str, error_msg)."""
    with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as tmp:
        rom_path = tmp.name
    try:
        rc, _, stderr = run([ASM, spl_path, rom_path])
        if rc != 0:
            return False, "", f"assembly failed: {stderr.strip()}"
        rc, stdout, stderr = run([VM, rom_path])
        out = stdout.decode("utf-8", errors="replace")
        if rc != 0:
            return False, out, f"vm exited with code {rc}: {stderr.strip()}"
        return True, out, ""
    finally:
        if os.path.exists(rom_path):
            os.unlink(rom_path)


def asm_error(source):
    """Assemble source text, return (returncode, stderr)."""
    with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        spl_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
        rom_path = f.name
    try:
        rc, _, stderr = run([ASM, spl_path, rom_path])
        return rc, stderr
    finally:
        os.unlink(spl_path)
        if os.path.exists(rom_path):
            os.unlink(rom_path)


def vm_error(source):
    """Assemble + run source text, return (asm_ok, vm_rc, vm_stderr)."""
    with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
        f.write(source)
        spl_path = f.name
    with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
        rom_path = f.name
    try:
        rc, _, stderr = run([ASM, spl_path, rom_path])
        if rc != 0:
            return False, rc, stderr
        rc, _, stderr = run([VM, rom_path])
        return True, rc, stderr
    finally:
        os.unlink(spl_path)
        if os.path.exists(rom_path):
            os.unlink(rom_path)


def main():
    passed = 0
    failed = 0
    total = 1 + len(ASM_ERROR_TESTS) + len(VM_ERROR_TESTS) + 2  # +2 = data bytecode tests

    print(f"Running {total} tests...\n")

    # --- test_all.spl: functional test covering every opcode ---
    expected = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcd\nAll 30 tests passed!\n"
    ok, actual, err = asm_and_run(TEST_ALL)
    if ok and actual == expected:
        print("  PASS  test_all.spl (30 opcode tests)")
        passed += 1
    else:
        print(f"  FAIL  test_all.spl")
        if err:
            print(f"        error: {err}")
        else:
            print(f"        expected: {expected!r}")
            print(f"        actual:   {actual!r}")
        failed += 1

    # --- Assembler error rejection ---
    for source, expected_err in ASM_ERROR_TESTS:
        label = f"asm rejects: {expected_err}"
        rc, stderr = asm_error(source)
        if rc != 0 and expected_err in stderr:
            print(f"  PASS  {label}")
            passed += 1
        else:
            print(f"  FAIL  {label}  (rc={rc}, stderr={stderr.strip()!r})")
            failed += 1

    # --- VM runtime error handling ---
    for source, expected_err in VM_ERROR_TESTS:
        label = f"vm catches: {expected_err}"
        asm_ok, rc, stderr = vm_error(source)
        if not asm_ok:
            print(f"  FAIL  {label}  (assembly failed)")
            failed += 1
        elif rc != 0 and expected_err in stderr:
            print(f"  PASS  {label}")
            passed += 1
        else:
            print(f"  FAIL  {label}  (rc={rc}, stderr={stderr.strip()!r})")
            failed += 1

    # --- data pseudo-instruction: bytecode verification ---
    data_bytecode_tests = [
        ("data numeric bytes",
         '(jump after)(data msg 72 101 108)(label after)(halt)',
         bytes([0x30, 0x00, 0x06, 72, 101, 108, 0x00])),
        ("data string syntax",
         '(jump after)(data msg "Hel")(label after)(halt)',
         bytes([0x30, 0x00, 0x06, 72, 101, 108, 0x00])),
    ]
    for label, source, expected_rom in data_bytecode_tests:
        with tempfile.NamedTemporaryFile(suffix=".spl", mode="w", delete=False, encoding="utf-8") as f:
            f.write(source)
            spl_path = f.name
        with tempfile.NamedTemporaryFile(suffix=".rom", delete=False) as f:
            rom_path = f.name
        try:
            rc, _, stderr = run([ASM, spl_path, rom_path])
            if rc != 0:
                print(f"  FAIL  {label}  (assembly failed: {stderr.strip()})")
                failed += 1
            else:
                with open(rom_path, 'rb') as f:
                    rom = f.read()
                if rom == expected_rom:
                    print(f"  PASS  {label}")
                    passed += 1
                else:
                    print(f"  FAIL  {label}  (expected {expected_rom.hex()}, got {rom.hex()})")
                    failed += 1
        finally:
            os.unlink(spl_path)
            if os.path.exists(rom_path):
                os.unlink(rom_path)

    # --- Summary ---
    print(f"\n{passed}/{total} passed", end="")
    if failed:
        print(f", {failed} failed")
        sys.exit(1)
    else:
        print()
        sys.exit(0)


if __name__ == "__main__":
    main()
