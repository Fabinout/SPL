# SPL Projects Overview

This repository contains multiple interconnected projects built on the **SPL (Structured Parenthesized Language)** specification and Python VM implementation.

## Projects

### 1. **SPL Language & VM** (Core Infrastructure)
📍 **Status:** Stable ✅
📁 **Location:** Root directory + `vm-python/`

The foundation of everything. Includes:
- **SPL-spec-fr.md** — Complete language specification (v1.0)
- **vm-python/spl_asm.py** — Assembler (2-pass, label resolution)
- **vm-python/spl_vm.py** — Stack-based VM with Harvard architecture
- **vm-python/tests/run_tests.py** — Automated test suite (29/29 passing)

**Key Features:**
- 8-bit stack-based execution
- 64 KiB RAM + separate ROM code space
- Port-mapped I/O (console, keyboard, video, audio, timer)
- Macro expansion, file inclusion, full assembler support

**Recent Enhancements:**
- Keyboard polling (0x24-0x27) for game development
- 60 FPS synchronization for real-time apps
- Video output via tkinter (FB8/FB16 modes)
- Drawing primitives (rectangle fill, line drawing via Bresenham)

---

### 2. **Pong Game** (Reference Implementation)
📍 **Status:** Complete (Reference) ✅
📁 **Location:** `examples/pong.spl` + `examples/pong-simple.spl`
📚 **Docs:** `docs/pong/`

A fully functional Pong game showcasing SPL capabilities.

**Files:**
- `examples/pong.spl` — Full version (207 instructions, 461 bytes)
  - 2 paddles, ball physics, collision detection
  - 160×120 monochrome display
  - Keyboard-controlled paddle + simple AI

- `examples/pong-simple.spl` — Debug version (69 instructions)
  - Single paddle for incremental testing
  - Clean architecture for learning

**Documentation:**
- `docs/pong/PONG-IMPLEMENTATION.md` — Master TODO & phases
- `docs/pong/PONG-STATUS-FINAL.md` — Final architecture & recommendations
- `docs/pong/PONG-BUGFIX.md` — Bug analysis & fixes
- `docs/pong/PONG-NOTES.md` — Game design & limitations
- `docs/pong/PHASE-1-ANALYSIS.md` — Specification requirements
- `docs/pong/PHASE-3-IMPLEMENTATION.md` — VM implementation details

**Lessons Learned:**
- How to structure real-time game loops in SPL
- Effective use of memory for game state
- Collision detection patterns
- Keyboard input polling vs events

---

### 3. **Flashcard App** (Current Development)
📍 **Status:** In Progress 🚧
📁 **Location:** Root directory
📚 **Plan:** `FLASHCARD_PLAN.md`
📋 **Task 2 Complete:** `TASK2_SUMMARY.md`

A terminal-based flashcard quiz application for learning (European capitals).

**Current Progress:**
- ✅ **Task 2:** String output instruction (`print-cstring`)
  - Opcode 0x42 for printing null-terminated strings
  - Spec update, VM implementation, assembler support
  - Example: Shakespeare's Sonnet 30 in `examples/poem.spl`

- 📋 **Task 1:** Data structure (pending)
  - Store 24 European capital flashcard pairs in memory

- 📋 **Task 3:** Main loop (pending)
  - Random card selection using RNG
  - Display question → wait for keypress → show answer

- 📋 **Task 4:** Testing (pending)

**Flashcard Data Format:**
```
ANSWER|QUESTION (in French)

Examples:
- Paris|Quelle est la capitale de la France?
- Berlin|Quelle est la capitale de l'Allemagne?
- (... 22 more ...)
```

**Architecture:**
```
Memory Layout:
├── 0x0000-0x0100: Working area (variables, temporary data)
├── 0x0100-0x1000: Flashcard strings (questions & answers)
└── 0x1000+:       Game loop code & state
```

---

## File Organization

```
SPL/
├── README.md                    ← Start here!
├── CLAUDE.md                    ← Project instructions
├── SPL-spec-fr.md               ← Language specification
├── FLASHCARD_PLAN.md            ← Flashcard app master plan
├── TASK2_SUMMARY.md             ← Completed Task 2 documentation
│
├── vm-python/                   ← VM & Assembler
│   ├── spl_asm.py               ← 2-pass assembler
│   ├── spl_vm.py                ← Stack-based virtual machine
│   └── tests/
│       ├── run_tests.py         ← Test suite (29/29 passing)
│       ├── test_all.spl         ← Comprehensive opcode tests
│       └── test_print_cstring.spl
│
├── examples/                    ← Example programs
│   ├── pong.spl                 ← Full Pong game
│   ├── pong-simple.spl          ← Simple Pong (debugging)
│   └── poem.spl                 ← Poetry output demo (Sonnet 30)
│
├── tests/                       ← Test programs
│   └── test_print_cstring.spl
│
└── docs/                        ← Documentation
    ├── PROJECTS.md              ← This file
    └── pong/
        ├── PONG-IMPLEMENTATION.md
        ├── PONG-STATUS-FINAL.md
        ├── PONG-BUGFIX.md
        ├── PONG-NOTES.md
        ├── PHASE-1-ANALYSIS.md
        └── PHASE-3-IMPLEMENTATION.md
```

---

## Quick Start

### Build & Run a Program
```bash
# Assemble
python3 vm-python/spl_asm.py examples/poem.spl -o poem.rom

# Run
python3 vm-python/spl_vm.py poem.rom
```

### Run Tests
```bash
python3 vm-python/tests/run_tests.py
```

### Run Pong Game
```bash
python3 vm-python/spl_asm.py examples/pong.spl -o pong.rom
python3 vm-python/spl_vm.py pong.rom
# Click window, use UP/DOWN or W/S to move paddle
```

---

## Architecture Highlights

### SPL VM Features
| Feature | Status | Details |
|---------|--------|---------|
| **Core I/O** | ✅ Complete | Console (0x01-0x03), RNG (0x10), Timer (0x11-0x14) |
| **Video** | ✅ Complete | FB8/FB16 modes, 160×120 to 320×240, tkinter display |
| **Keyboard** | ✅ Complete | Polling (0x24-0x27) for UP/DOWN/LEFT/RIGHT |
| **Audio** | ✅ Complete | PSG 4-channel synthesizer (via sounddevice) |
| **Mouse** | ✅ Complete | Position + buttons (0x70-0x77) |
| **Drawing** | ✅ Complete | Rectangle fill + Bresenham line (0x3E-0x3F) |
| **String Output** | ✅ Complete | null-terminated strings (0x42, `print-cstring`) |

### VM Specifications
- **Architecture:** Harvard (separate code/data)
- **Word size:** 8-bit (0-255)
- **Memory:** 64 KiB RAM + ROM code space
- **Work stack:** 256 entries (8-bit)
- **Return stack:** 64 entries (16-bit addresses)
- **Address mode:** Big-endian for 16-bit values
- **Synchronization:** 60 FPS via V-sync on VID_FLIP

---

## Development Guidelines

### When Starting New Work
1. **Check FLASHCARD_PLAN.md** for current task
2. **Read relevant docs** in `docs/pong/` for similar patterns
3. **Write tests first** — add to `vm-python/tests/run_tests.py`
4. **Keep the spec updated** — any new features go in SPL-spec-fr.md

### File Naming
- **Programs:** `examples/*.spl` for polished demos, `tests/*.spl` for unit tests
- **Docs:** Follow project scope (`FLASHCARD_*.md`, `PONG_*.md`)
- **Code:** Follow Python PEP-8 in `vm-python/`

### Commit Convention
```
Task description (short summary)

## Summary
- What changed and why

## Files
- List of changed files

Co-Authored-By: Claude Haiku 4.5 <noreply@anthropic.com>
```

---

## Next Steps

### Flashcard App
- [ ] Task 1: Embed flashcard data in SPL program
- [ ] Task 2: ✅ DONE — String output instruction
- [ ] Task 3: Main loop with RNG selection
- [ ] Task 4: Testing & debugging

### Future Enhancements
- Add keyboard input for answers (requires keyboard event mode)
- Score tracking with memory persistence
- Multiple flashcard sets
- Repeat missed questions

### Reference Projects
- Extend Pong with scoring, sound, color
- Create other games (Breakout, Snake, etc.)
- Build educational apps (math trainer, spelling bee)

---

## Resources

| Resource | Location |
|----------|----------|
| Language Spec | `SPL-spec-fr.md` |
| VM Source | `vm-python/spl_vm.py` |
| Assembler | `vm-python/spl_asm.py` |
| Test Suite | `vm-python/tests/run_tests.py` |
| Pong Docs | `docs/pong/` |
| Flashcard Plan | `FLASHCARD_PLAN.md` |

---

**Last Updated:** 2026-02-24
**Maintainer:** Claude Code (Anthropic)
