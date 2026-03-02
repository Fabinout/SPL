# Task 2: String Output (print-cstring) — COMPLETED ✅

## Overview
Task 2 implemented a **string printing capability** for SPL, enabling the flashcard app to display text-based content efficiently. This involved updating the spec, implementing in the VM and assembler, and adding comprehensive tests.

## Changes Made

### 1. **Spec Update** (SPL-spec-fr.md)
Added a new instruction: **`(print-cstring address16)`**

- **Opcode**: `0x42`
- **Args**: 2-byte big-endian address
- **Behavior**: Reads bytes from memory starting at `address16` until encountering a null terminator (`0x00`), outputting each non-null byte to the console
- **Stack**: No stack impact (non-destructive)
- **Location**: Section 6.5.1 (new subsection in I/O)
- **Opcode Table**: Updated to include the new instruction

### 2. **VM Implementation** (vm-python/spl_vm.py)
- Added `OP_PRINT_CSTRING = 0x42` opcode definition
- Implemented handler in the main execution loop:
  - Reads the 16-bit address from bytecode
  - Validates address is within memory bounds
  - Loops through memory bytes until null terminator
  - Appends non-null bytes to console buffer
  - Respects existing console buffering/flushing behavior

### 3. **Assembler Support** (vm-python/spl_asm.py)
- Added `'print-cstring': (0x42, 'addr16')` to `INSTRUCTIONS` table
- Supports numeric addresses only (16-bit, like `load`/`store`)
- Full two-pass assembly pipeline support

### 4. **Tests & Examples**

#### Unit Test: `tests/test_print_cstring.spl`
Tests basic string printing functionality:
```spl
; Store "Hello" and "World" in RAM, print both with newlines
; Verifies: correct null-termination handling, byte-by-byte output
```
**Status**: ✅ PASS

#### Example Program: `examples/poem.spl`
A beautiful 4-line poem demonstrating string output:
```
The moon shines bright tonight
Stars twinkle in the sky
A gentle breeze flows free
In dreams we are at peace
```
- 231 SPL instructions, 574 bytes of bytecode
- Stores strings in memory (0x0100–0x0179)
- Uses 4x `print-cstring` calls with newlines
- **Output**: Properly formatted poem

#### Integration: Test Suite (`vm-python/tests/run_tests.py`)
Added automated test for print-cstring in the test runner pipeline
- Runs `test_print_cstring.spl`
- Validates output contains "Hello\nWorld\n"
- **Status**: ✅ PASS (29/29 total tests passing)

## Design Decisions

1. **Address-only argument** (`addr16` vs. `target16`)
   - Follows SPL design principle: `load`/`store` use numeric addresses only
   - Simpler to implement, aligns with architecture

2. **Null-termination semantics**
   - Standard C-style strings simplify memory layout
   - Single null byte marks end; not printed
   - Memory efficient for flashcard content

3. **No stack interaction**
   - Pure output operation, doesn't affect stack
   - Consistent with port-based I/O model

4. **Console buffering integration**
   - Appends to existing `console_buf` (list of bytes)
   - Works seamlessly with auto-flush on `\n` and port `0x03`
   - No new infrastructure needed

## Verification

```bash
$ python3 vm-python/spl_asm.py tests/test_print_cstring.spl -o test.rom
Assembled 31 instructions -> 75 bytes

$ python3 vm-python/spl_vm.py test.rom
Hello
World
```

```bash
$ python3 vm-python/tests/run_tests.py
... (28 existing tests pass) ...
  PASS  test_print_cstring.spl (string output)
29/29 passed
```

## Next Steps
- Task 1: Create SPL data structure for flashcards (embed in program)
- Task 3: Create main program loop with random selection and display
- Task 4: Test the complete flashcard system
- Future: Add keyboard input support for interactivity

## Files Modified
- `SPL-spec-fr.md` — added section 6.5.1 and updated opcode table
- `vm-python/spl_vm.py` — added opcode definition and execution handler
- `vm-python/spl_asm.py` — added instruction to assembler table
- `vm-python/tests/run_tests.py` — added print-cstring test

## Files Created
- `tests/test_print_cstring.spl` — unit test
- `examples/poem.spl` — example output program
- `TASK2_SUMMARY.md` — this document
