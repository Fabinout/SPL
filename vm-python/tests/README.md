# SPL VM - Comprehensive Test Suite

## Quick Start

Run all tests with the master runner:

```bash
cd vm-python
bash tests/run_all_tests.sh
```

Or run the extended core test suite:

```bash
cd vm-python
python3 tests/run_tests.py
```

## Test Files Overview

### Existing Tests (Maintained)

- **`test_all.spl`** - 30 opcode functional tests (all stack, arithmetic, logic, memory, control flow, I/O, and comparison opcodes)
- **`run_tests.py`** - 22 automated tests covering assembler validation, VM error handling, macros, includes, and data pseudo-instruction (EXTENDED to 28+ tests)
- **`test_drawing_primitives.py`** - 11 graphics unit tests (rectangle fill, Bresenham lines, clipping, multiple video modes)

### New Tests (Added)

#### SPL Functional Tests
- **`test_indirect.spl`** (6 tests) - Indirect addressing opcodes (load-indirect, store-indirect) with boundary addresses
- **`test_memory_bounds.spl`** (4 tests) - Direct and indirect memory access at boundaries (0x0000, 0xFFFF)
- **`test_stack_limits.spl`** (2 tests) - Stack edge cases and return stack nesting
- **`test_timer.spl`** (4 tests) - Timer port latching behavior (0x11-0x14)
- **`test_edge_values.spl`** (8 tests) - Arithmetic wrapping, operand order, comparison edge cases
- **`test_io_ports.spl`** (15 tests) - All I/O subsystems (console, RNG, timer, video, audio, mouse, SYSCTL_CAPS)

#### Python Test Modules
- **`test_string_escapes.py`** (7 tests) - String escape sequences in data pseudo-instruction
- **`test_error_injection.py`** (10+ tests) - All error conditions (stack/return overflow, OOB memory, truncated bytecode, unknown opcodes)
- **`test_fuzzing.py`** (~1600 tests) - Random bytecode, boundary values, malformed input with shrinking
- **`test_properties.py`** (~700 tests) - Invariant testing (commutativity, associativity, identity, memory persistence, call/return balance)

#### Master Runner
- **`run_all_tests.sh`** - Orchestrates all test suites with color-coded output and summary

## Test Statistics

| Component | Count | Status |
|-----------|-------|--------|
| Opcode coverage | 32/32 | ✓ 100% |
| I/O ports | 40+ | ✓ Tested |
| Error conditions | 12+ | ✓ Tested |
| Assembler validation | 20+ | ✓ Tested |
| Edge cases | 50+ | ✓ Tested |
| **Total tests** | **~2400+** | **✓ All passing** |

## Running Individual Tests

### SPL Program Tests
```bash
# Test indirect addressing
python3 spl_asm.py tests/test_indirect.spl /tmp/test.rom
python3 spl_vm.py /tmp/test.rom
# Expected output: ABCDEF (with newline)

# Test edge values
python3 spl_asm.py tests/test_edge_values.spl /tmp/test.rom
python3 spl_vm.py /tmp/test.rom
# Expected output: ABCDEFGH (with newline)

# Test I/O ports
python3 spl_asm.py tests/test_io_ports.spl /tmp/test.rom
python3 spl_vm.py /tmp/test.rom
# Expected output: ABCDEFGHIJKLMNO (with newline)
```

### Python Unit Tests
```bash
# String escape sequences
python3 -m unittest tests.test_string_escapes -v

# Error injection (stack overflow, OOB memory, etc.)
python3 -m unittest tests.test_error_injection -v

# Fuzzing tests (random bytecode, boundary values)
timeout 60 python3 -m unittest tests.test_fuzzing -v

# Property-based tests (invariants across random inputs)
timeout 60 python3 -m unittest tests.test_properties -v

# Graphics primitives
python3 -m unittest tests.test_drawing_primitives -v
```

### Core Test Suite (Extended)
```bash
python3 tests/run_tests.py
```

## Test Coverage Details

### Opcodes (100% Coverage)

All 32 opcodes tested:
- Stack: `push`, `drop`, `dup`, `swap`, `over` ✓
- Arithmetic: `add`, `sub`, `mul`, `div`, `mod` ✓
- Logic: `and`, `or`, `xor`, `not` ✓
- Comparison: `lt`, `gt` ✓
- Memory: `load`, `store`, `load-indirect`, `store-indirect` ✓ **NEW**
- Control: `jump`, `jump-if-zero`, `jump-if-not-zero`, `call`, `return`, `halt` ✓
- I/O: `in`, `out` ✓

### I/O Ports (40+ Tested)

- Console (0x01-0x03): write, read status, flush
- RNG (0x10): random byte
- Timer (0x11-0x14): 32-bit millisecond counter with latching
- Video (0x30-0x3F): mode, resolution, stride, FB address, status, flip, clear, rect, line
- Audio (0x50-0x59): channels, frequency, volume, waveform, gate, master volume
- Mouse (0x70-0x77): position, buttons, wheel
- System (0xFF): capabilities

### Error Conditions (12+ Tested)

- Stack overflow (257 pushes)
- Stack underflow (operations on empty stack)
- Return stack overflow (65+ nested calls)
- Return stack underflow (return without call)
- Memory out-of-bounds (load/store/indirect at 0x10000+)
- Truncated bytecode (push without arg, jump with incomplete address)
- Unknown opcodes
- PC past end of bytecode
- Division/modulo by zero (returns 0, not fault)

### Edge Cases (50+ Tested)

- Boundary values: 0, 1, 127, 128, 254, 255
- Boundary addresses: 0x0000, 0xFFFF
- Arithmetic wrapping (255+1=0, 0-1=255, 128×2=0)
- String escapes: `\n`, `\t`, `\\`, `\"`, `\0`, mixed
- Memory boundaries (direct and indirect at 0x0000, 0xFFFF)
- Timer latching cycles
- Comparison edge cases (equal values, operand order)

## Implementation Notes

### Stack Order Peculiarity

The indirect addressing instructions have specific stack ordering:

**load-indirect** (0x22):
- Expects stack [hi (bottom), lo (top)]
- Pops: lo first, then hi
- Address = (hi << 8) | lo
- Usage: `push hi; push lo; load-indirect`

**store-indirect** (0x23):
- Expects stack [val (bottom), hi, lo (top)]
- Pops: lo first, then hi, then val
- Address = (hi << 8) | lo
- Stores: value to address
- Usage: `push val; push hi; push lo; store-indirect`

### Test Validation Strategies

1. **Functional Testing (SPL)**: Self-contained programs with letter output
   - Used for: opcode validation, I/O testing, edge cases
   - Format: Output A-Z on pass, '!' on fail

2. **Unit Testing (Python)**: Precise bytecode and error validation
   - Used for: assembler validation, escape sequences, error conditions
   - Framework: Python `unittest`

3. **Fuzzing**: Random bytecode generation with crash detection
   - Used for: robustness validation, edge case discovery
   - Strategies: random bytecode, boundary values, malformed input
   - Features: shrinking for minimal reproducers

4. **Property-Based Testing**: Invariant checking with random inputs
   - Used for: mathematical properties, correctness verification
   - Properties: commutativity, associativity, identity, memory persistence

## Continuous Integration

The test suite is CI/CD friendly:

```bash
cd vm-python
bash tests/run_all_tests.sh
exit_code=$?
```

- Exit code 0: All tests passed
- Exit code 1: One or more tests failed
- Color-coded output (Green: pass, Red: fail, Yellow: skip)
- Summary with test counts

## Troubleshooting

### Test Timeout

Some fuzzing tests may timeout on very slow systems. Adjust timeout in shell script:

```bash
# In run_all_tests.sh
timeout 120 python3 -m unittest tests.test_fuzzing  # 120 seconds
```

### Missing Dependencies

Ensure you have Python 3.6+ installed. The test suite uses only standard library:

```bash
python3 --version  # Should be 3.6+
```

### Test Failure

If a test fails, run it individually for details:

```bash
python3 tests/run_tests.py
# Or
python3 -m unittest tests.test_error_injection.TestStackOverflow -v
```

## Documentation

For complete details on test strategy, coverage, and implementation, see:

- **`TEST_SUITE_SUMMARY.md`** - Comprehensive test suite overview and statistics

## Contributing

To add new tests:

1. **For SPL programs**: Create `test_xxx.spl` following the pattern of existing tests (output letters on pass)
2. **For Python tests**: Create `test_xxx.py` using `unittest` framework
3. **Update run_tests.py**: Add integration of new test files
4. **Run all tests**: Ensure `run_all_tests.sh` passes

## License

Tests are part of the SPL project and follow the same license as the main codebase.

---

**Last Updated**: 2026-02-15
**Test Suite Version**: 2.0 (Comprehensive)
**Status**: ✓ All tests passing (~2400+ tests)
