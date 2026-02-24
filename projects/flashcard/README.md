# Flashcard Learning Application

A fully interactive flashcard application for learning European capital cities in French.

## Overview

This SPL program demonstrates:
- **Data structures** — 24 flashcard pairs stored efficiently in ROM
- **Random selection** — Using the RNG port for random flashcard selection
- **Keyboard input** — Event-driven input handling with keyboard polling
- **Complex dispatch** — Jump-based dispatching to 24 different card routines
- **String output** — ROM-based string printing for efficient storage

## How to Use

### Assemble and Run

```bash
# From project root
python3 vm-python/spl_asm.py projects/flashcard/flashcard-app.spl
python3 vm-python/spl_vm.py projects/flashcard/flashcard-app.rom
```

### Interactive Usage

1. A window opens with instructions
2. Read the French question displayed in the console
3. Press **any key** to reveal the answer
4. A new random flashcard appears
5. Repeat indefinitely

## Example Session

```
Quelle est la capitale de l'Italie?
[Press any key]

Rome

Quelle est la capitale de la Suede?
[Press any key]

Stockholm

Quelle est la capitale de la France?
[Press any key]

Paris
```

## Files

- **flashcard-app.spl** — Main program with random selection and keyboard input (401 instructions)
- **flashcard-data.spl** — Data structure containing all 24 European capitals

## Architecture

### Data Storage

All 24 flashcard pairs are stored as ROM data:
```lisp
(data ans-1 "Paris" 0)
(data que-1 "Quelle est la capitale de la France?" 0)
; ... (22 more pairs)
```

### Random Selection

The program uses the RNG port to randomly select cards:
```lisp
(in 0x10)        ; Read RNG (0-255)
(push 24)        ; Modulo 24
(mod)            ; Result: 0-23 index
```

### Keyboard Waiting

Waits for user keypress before showing answer:
```lisp
(label wait-for-input)
(in 0x21)                    ; Check KBD_STATUS
(push 1)(and)                ; Extract bit0 (data ready)
(jump-if-zero wait-for-input) ; Loop if no key
(in 0x20)                    ; Read key from KBD_DATA
(drop)                       ; Discard key code
```

## Flashcard Data

All 24 European capital questions in French:

1. France → Paris
2. Germany → Berlin
3. Spain → Madrid
4. Italy → Rome
5. Netherlands → Amsterdam
6. Austria → Vienne
7. Poland → Varsovie
8. Czech Republic → Prague
9. Greece → Athenes
10. Portugal → Lisbonne
11. Sweden → Stockholm
12. Denmark → Copenhague
13. Belgium → Bruxelles
14. Switzerland → Berne
15. Romania → Bucarest
16. Hungary → Budapest
17. Slovakia → Bratislava
18. Slovenia → Ljubljana
19. Croatia → Zagreb
20. Serbia → Belgrade
21. Bulgaria → Sofia
22. Finland → Helsinki
23. Iceland → Reykjavik
24. Ireland → Dublin

## Statistics

| Metric | Value |
|--------|-------|
| **Instructions** | 401 |
| **Bytecode** | 1,810 bytes |
| **Flashcards** | 24 pairs |
| **ROM Data** | All flashcard strings |
| **Dispatch entries** | 24 (one per card) |

## Future Enhancements

- Score tracking (count correct/incorrect)
- Timed mode (reveal after delay instead of keypress)
- Multiple card categories
- Progress persistence
- Categories/difficulty levels

## Testing

Unit tests are in `tests/projects/flashcard/`:
- `test_flashcard_data.spl` — Data structure verification
- `test_flashcard_app.spl` — Main loop verification

Run tests with:
```bash
python3 vm-python/tests/run_tests.py
```
