# SPL Indirect Addressing — Native Implementation

## Overview

SPL now supports **native indirect addressing** through two instructions:
- `load-indirect` — Read from a dynamically calculated RAM address
- `store-indirect` — Write to a dynamically calculated RAM address

This enables proper dynamic RAM manipulation without the need for loop unrolling or code generation.

## Instructions

### `load-indirect` (opcode 0x22)

**Purpose:** Read a byte from a calculated memory address.

**Stack convention:**
```
Before: ... HI LO
After:  ... VALUE
```

**Semantics:**
```
lo = pop()
hi = pop()
addr = (hi << 8) | lo
push(memory[addr])
```

**Address calculation:** `addr = (HI << 8) | LO`
- `HI` is the high byte (0x00–0xFF)
- `LO` is the low byte (0x00–0xFF)
- Supports full 16-bit address space (0x0000–0xFFFF)

**Example:**
```spl
; Read from address 0x0200
(push 0x02)         ; HI (goes to stack bottom)
(push 0x00)         ; LO (goes to stack top)
(load-indirect)     ; Reads byte from 0x0200, pushes on stack

; Now the byte value is on the stack
(out 0x01)          ; Display it
```

### `store-indirect` (opcode 0x23)

**Purpose:** Write a byte to a calculated memory address.

**Stack convention:**
```
Before: ... VALUE HI LO
After:  ...
```

**Semantics:**
```
lo = pop()
hi = pop()
val = pop()
addr = (hi << 8) | lo
memory[addr] = val
```

**Address calculation:** Same as `load-indirect`

**Example:**
```spl
; Write 42 to address 0x0100
(push 42)           ; VALUE (goes to stack bottom)
(push 0x01)         ; HI
(push 0x00)         ; LO (goes to stack top)
(store-indirect)    ; Writes 42 to address 0x0100
```

## Common Patterns

### Buffer Operations with Dynamic Index

```spl
; Pseudo-code: buffer[index] = value
; Assumes: index on stack

; Calculate address: base_hi, base_lo = constants
; addr_lo = base_lo + index
; addr_hi = base_hi + (addr_lo overflow)

; Simplified for base_lo < 128 (no carry):
(push 0x02)         ; HI of base 0x0200
(over)              ; Duplicate index
(push 0x00)         ; LO of base
(add)               ; 0x00 + index = new LO
(swap)              ; Stack: [value, index, HI, new_LO]
(push 3)            ; Adjust stack
(roll)              ; Rotate to get [value, HI, new_LO] pattern
(store-indirect)
```

### Sequential Buffer Write

```spl
(label write-buffer-loop)
(dup)                   ; index
(push 64)
(sub)
(jump-if-zero done)

; Write to buffer[index]
(push 0x02)             ; HI of buffer base
(over)                  ; Duplicate index
(push 0x00)             ; LO of base
(add)                   ; Calculate LO
; Stack: [... index, HI, calc_LO]
(over)                  ; Get value somehow
(swap)                  ; Adjust to [value, HI, LO]
(store-indirect)

(push 1)
(add)
(jump write-buffer-loop)

(label done)
(drop)
```

### Reading a String from RAM

```spl
(label print-cstring-indirect)
; Expects: HI, LO on stack (address of string)

(label print-loop)
(load-indirect)     ; Load byte at (HI, LO)
(dup)
(push 0)            ; Check if null terminator
(sub)
(jump-if-zero print-done)

(out 0x01)          ; Print character

; Increment address
; (This is tricky with 16-bit addresses — see advanced patterns)

(jump print-loop)

(label print-done)
(drop)
(return)
```

## Memory Layout Recommendations

### For Buffer Operations

If you need to manipulate buffers dynamically:

1. **Use PAGE-ALIGNED BUFFERS** (easier math)
   ```
   BUFFER_BASE = 0x0200 (page 0x02)
   ELEMENT = base_addr + index
   addr_hi = 0x02
   addr_lo = 0x00 + index
   ```

2. **Keep indices small** (< 128) to avoid LO overflow
   ```
   Max safe index: 127 (before carry to HI)
   For larger indices, must handle carry manually
   ```

3. **Allocate per-page**
   ```
   Array 0: 0x0200–0x02FF (256 elements)
   Array 1: 0x0300–0x03FF (256 elements)
   Array 2: 0x0400–0x04FF (256 elements)
   ```

## Testing

Run the comprehensive test suite:

```bash
python3 vm-python/spl_asm.py vm-python/tests/test_indirect_addressing.spl /tmp/test.rom
SPL_NO_GUI=1 python3 vm-python/spl_vm.py /tmp/test.rom
```

Expected output: `ABCDE` (all 5 test groups pass)

## Use Cases

### 1. Dynamic Buffer Manipulation
- Reading user input into a buffer
- Storing variable-length strings
- Implementing circular buffers

### 2. Array-like Data Structures
- Simple arrays with dynamic indexing
- Matrix storage (with row/column calculation)
- Lookup tables in RAM

### 3. Self-Modifying Code / State Machines
- Storing program state in RAM
- Dynamic configuration data
- Running computed sequences

### 4. File I/O with Buffering
- Reading/writing blocks from files
- Accumulating data before flush
- Sequential data processing

## Stack Discipline Notes

For safety and clarity:

1. **Always dup/over/swap carefully** — stack operations with indirect addressing can be tricky
2. **Test with small examples first** — verify stack before committing to loops
3. **Use comments** — document what's on the stack at each step
4. **Draw pictures** — literally sketch the stack to avoid mistakes

## Error Handling

If you try to access memory outside 0x0000–0xFFFF:
- VM will halt with: `fault: load-indirect: address 0xXXXX out of bounds`
- Current RAM: 64 KiB (0x0000–0xFFFF)

## Historical Note

This native indirect addressing replaces workarounds like:
- **Loop unrolling** — generates one store-indirect per offset (64+ instructions)
- **Redesign circumvention** — avoiding dynamic addressing entirely

Now, clean, natural dynamic addressing is possible!
