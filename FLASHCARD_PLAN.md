# SPL Flashcard App - Implementation Plan

## Flashcard Data (European Capitals)

Format: `ANSWER|QUESTION` (all questions in French)

```
Paris|Quelle est la capitale de la France?
Berlin|Quelle est la capitale de l'Allemagne?
Madrid|Quelle est la capitale de l'Espagne?
Rome|Quelle est la capitale de l'Italie?
Amsterdam|Quelle est la capitale des Pays-Bas?
Vienne|Quelle est la capitale de l'Autriche?
Varsovie|Quelle est la capitale de la Pologne?
Prague|Quelle est la capitale de la République tchèque?
Athènes|Quelle est la capitale de la Grèce?
Lisbonne|Quelle est la capitale du Portugal?
Stockholm|Quelle est la capitale de la Suède?
Copenhague|Quelle est la capitale du Danemark?
Bruxelles|Quelle est la capitale de la Belgique?
Berne|Quelle est la capitale de la Suisse?
Bucarest|Quelle est la capitale de la Roumanie?
Budapest|Quelle est la capitale de la Hongrie?
Bratislava|Quelle est la capitale de la Slovaquie?
Ljubljana|Quelle est la capitale de la Slovénie?
Zagreb|Quelle est la capitale de la Croatie?
Belgrade|Quelle est la capitale de la Serbie?
Sofia|Quelle est la capitale de la Bulgarie?
Helsinki|Quelle est la capitale de la Finlande?
Reykjavik|Quelle est la capitale de l'Islande?
Dublin|Quelle est la capitale de l'Irlande?
```

## Implementation Tasks

### Task 1: Create SPL data structure for flashcards
- ✅ Embedded all 24 flashcard pairs in examples/flashcard-data.spl
- ✅ Used (data) pseudo-instruction with print-rom-string for efficient storage
- ✅ Created label-based lookup mechanism (ans-1...ans-24, que-1...que-24)
- ✅ Created test file (tests/test_flashcard_data.spl)
- ✅ All tests passing (31/31)
- ✅ Code size: 89 instructions, 1,252 bytes for 24 flashcards
- **Status**: ✅ COMPLETED

### Task 2: Create string printing function in SPL
- ✅ Added `(print-cstring address16)` instruction to spec
- ✅ Implemented in VM (spl_vm.py) with opcode 0x42
- ✅ Updated assembler (spl_asm.py) to support instruction
- ✅ Created unit test (tests/test_print_cstring.spl)
- ✅ Created example poem (examples/poem.spl)
- ✅ All tests passing (29/29)
- **Status**: ✅ COMPLETED

### Task 3: Create main program loop
- ✅ Initialize the flashcard data (using Task 1 structure)
- ✅ Pick a random flashcard using RNG (0x10)
- ✅ Display the question (using print-rom-string)
- ✅ Use a delay (busy-wait loop) to let user read
- ✅ Display the answer
- ✅ Loop to next question (main-loop)
- ✅ Created examples/flashcard-app.spl with dispatch mechanism
- ✅ Created test file (tests/test_flashcard_app.spl)
- ✅ All tests passing (32/32)
- **Status**: ✅ COMPLETED

### Task 4: Test the program
- Assemble and run the SPL program
- Verify all flashcards display correctly
- Verify RNG selection works
- **Status**: Pending

### Task 5 (Future): Add keyboard input support
- Extend vm-python to support keyboard input
- Modify SPL program to wait for keypress between question and answer
- **Status**: Future enhancement

### Task 6 (Future): Add other features
- Menu system to select difficulty/categories
- Score tracking
- Repeat missed questions
- **Status**: Future enhancement

## Notes
- Total flashcards: 24
- Data will be stored in memory starting at a safe offset (e.g., 0x1000)
- Each string stored null-terminated or with length prefix
- RNG will pick a random card: `(in 0x10) (mod 24)` to get 0-23 index
