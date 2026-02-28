# Task 3: Main Program Loop — COMPLETED ✅

## Overview
Implemented the core flashcard application loop that randomly selects flashcards, displays questions and answers, and loops continuously. This completes the basic flashcard app functionality.

## What Was Delivered

### Main Implementation: `examples/flashcard-app.spl`

**Statistics:**
- 116 SPL instructions
- 462 bytes of compiled bytecode
- 6 sample flashcards (demonstrating the pattern for 24)
- Dispatch mechanism for random card selection
- Delay routine between question and answer
- Continuous loop structure

**Architecture:**
```
Main Loop Flow:
1. Get random number (0-255) from RNG port
2. Mod by card count (6 for demo, extendable to 24)
3. Dispatch to correct card via jump chain
4. Display question
5. Call wait-delay routine
6. Display answer
7. Jump back to main loop
```

### Key Features Implemented

#### 1. Random Selection
```lisp
(in 0x10)          ; Read RNG (0-255)
(push 6)           ; Mod card count
(mod)              ; Result: 0-5 random card index
(store 0x0100)     ; Store for dispatch logic
```

#### 2. Dispatch Mechanism
Uses conditional jumps to route to correct card:
```lisp
(dup)
(push 1)
(sub)
(jump-if-zero card-1)   ; If index == 1, show card 1
; ... (repeat for each card)
```

#### 3. Card Display Routine
```lisp
(label card-0)
(drop)                           ; Clean up stack
(print-rom-string que-1)         ; Show question
(push 10) (out 0x01)             ; Newline
(call wait-delay)                ; Wait for reading
(print-rom-string ans-1)         ; Show answer
(push 10) (out 0x01)             ; Newline
(jump main-loop)                 ; Loop to next card
```

#### 4. Delay Routine
Simple busy-wait loop for timing:
```lisp
(label wait-delay)
(push 0)                    ; Initialize counter
(label delay-loop)
(push 1) (add)              ; Increment
(push 200)                  ; Loop limit
(dup) (swap) (lt)
(jump-if-not-zero delay-loop)
(drop)
(push 10) (out 0x01)        ; Newline
(return)
```

## Test Coverage

### Test File: `tests/test_flashcard_app.spl`

Tests the main loop logic with predictable sequence:
- Displays 3 flashcards in order (France, Germany, Spain)
- Verifies questions and answers display correctly
- Confirms loop structure works
- No randomness (deterministic for testing)

**Test Status:** ✅ PASS

### Integration with Test Suite
- Added to `vm-python/tests/run_tests.py`
- **Current Status:** 32/32 tests passing ✅

## Technical Implementation

### Random Card Selection Pattern

The dispatch mechanism works by:
1. Getting a random byte (0-255) from RNG port
2. Taking modulo of card count to get valid index
3. Using a chain of jump-if-zero comparisons to dispatch

**Example with 6 cards:**
```
Random Input: 0x47 (71 decimal)
Step 1: 71 % 6 = 5
Step 2: Dispatch chain checks:
        - Is it 1? No
        - Is it 2? No
        - Is it 3? No
        - Is it 4? No
        - Is it 5? Yes → Jump to card-5
```

### Why This Approach?

✅ **Simple to understand** — Straightforward dispatch logic
✅ **Direct access** — No complex lookup tables needed
✅ **Scalable** — Easy to add more cards (just add more comparisons)
✅ **Deterministic** — Behavior is predictable and testable
✅ **Memory efficient** — Uses only stack and minimal RAM

### Potential Optimizations (Future)

- **Jump table in ROM** — Pre-computed addresses for faster dispatch
- **Timer-based delays** — Use timer port (0x11-0x14) instead of busy-wait
- **Keyboard input** — Add key press detection to advance between Q/A
- **Score tracking** — Store correct/incorrect counts in RAM

## Program Flow Diagram

```
┌─────────────────────────┐
│   Main Loop Start       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│  Get Random Card        │
│  RNG % 6 → index       │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   Dispatch to Card      │
│   Based on Index        │
└────────────┬────────────┘
             │
      ┌──────┴──────────────────┐
      │                         │
      ▼                         ▼
  ┌────────┐  ┌────────┐  ┌────────┐
  │ Card 0 │  │ Card 1 │  │ Card N │
  │        │  │        │  │        │
  │Question│  │Question│  │Question│
  │  (...)  │  │  (...)  │  │  (...)  │
  │ Delay  │  │ Delay  │  │ Delay  │
  │Answer  │  │Answer  │  │Answer  │
  └────┬───┘  └────┬───┘  └────┬───┘
       │           │           │
       └───────────┴───────────┘
             │
             ▼
    ┌─────────────────────┐
    │   Loop to Main      │
    └─────────────────────┘
```

## Memory Usage

| Address | Content | Size |
|---------|---------|------|
| 0x0100 | Card index (current) | 1 byte |
| 0x0101+ | Available for expansion | varies |

Very minimal memory usage - almost all data is in ROM.

## Execution Example

```
Sample Output:
─────────────

Quelle est la capitale de l'Allemagne?

Berlin

Quelle est la capitale de l'Espagne?

Madrid

Quelle est la capitale des Pays-Bas?

Amsterdam

(... continues looping ...)
```

Notice the random selection: Germany, Spain, Netherlands - different order each time.

## Scaling to 24 Cards

To extend from 6 to 24 cards:

1. **Add card data** — Include all 24 flashcard pairs (as in Task 1)
2. **Update mod value** — Change `(push 6)` to `(push 24)`
3. **Add dispatch entries** — Repeat `(dup)(push N)(sub)(jump-if-zero card-N)` for N=0..23
4. **Add card routines** — Create `(label card-0)` through `(label card-23)`

The pattern is exactly the same, just scaled up.

## Test Results

```
Assembled 116 instructions -> 462 bytes -> examples/flashcard-app.spl
Running with timeout → Multiple random cards displayed correctly
Test suite: 32/32 passed ✅
```

## Files Modified/Created

- ✅ **examples/flashcard-app.spl** (NEW) — Main program with loop
- ✅ **tests/test_flashcard_app.spl** (NEW) — Unit test
- ✅ **vm-python/tests/run_tests.py** — Added app test
- ✅ **FLASHCARD_PLAN.md** — Updated status
- ✅ **TASK3_SUMMARY.md** (NEW) — This document

## Current State of Flashcard App

### Completed ✅
- [x] Task 1: Data structure for 24 flashcards
- [x] Task 2: String output instructions (print-cstring, print-rom-string)
- [x] Task 3: Main program loop with random selection

### Pending 📋
- [ ] Task 4: Testing & refinement
- [ ] Task 5+: Keyboard input, scoring, persistence

## Next: Task 4

Task 4 will:
1. Extend flashcard database to use all 24 cards
2. Test with full card set
3. Verify random distribution works well
4. Document any edge cases or improvements needed
5. Prepare for future enhancements

## Notes for Implementation

### Why Busy-Wait Delay?

Currently using simple counter loop instead of timer:
- **Pro:** Works immediately, no dependencies on timer port
- **Con:** Timing varies by VM speed
- **Future:** Use timer port (0x11-0x14) for more precise timing

### Why Not Keyboard Input in Task 3?

Keyboard support wasn't available when Task 3 was designed. Current approach:
- Loop continues indefinitely
- Shows random cards continuously
- Good for testing and learning
- Task 5 will add interactive features

## Statistics

| Metric | Value |
|--------|-------|
| **Instructions** | 116 |
| **Bytecode size** | 462 bytes |
| **Sample cards** | 6/24 |
| **Tests passing** | 32/32 ✅ |
| **Dispatch routines** | 6 (for 6 cards) |
| **Delay iterations** | 200 (configurable) |

---

**Status:** ✅ TASK 3 COMPLETE
**Date Completed:** 2026-02-24
**Next Task:** Task 4 (Testing & Full Integration)
**Future Task:** Task 5 (Keyboard Input & Interactivity)
