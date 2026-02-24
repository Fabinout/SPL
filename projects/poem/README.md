# Shakespeare's Sonnet 30 — French Translation

A demonstration of efficient string handling using the `print-rom-string` instruction.

## Purpose

This project showcases:
- **ROM-based string storage** — Embedding text directly in bytecode for efficiency
- **Data pseudo-instruction** — Using `(data)` to define string constants
- **print-rom-string opcode** — Printing strings from bytecode (ROM)

## How to Run

```bash
python3 vm-python/spl_asm.py projects/poem/poem.spl
python3 vm-python/spl_vm.py projects/poem/poem.rom
```

## Output

Displays Shakespeare's Sonnet 30 in French translation:

```
Quand ma pensée s'isole en doux silence,
J'invoque à mon secours le temps jadis,
Errant parmi les fantômes du passé,
Murmure les noms qu'oublie le présent.

Puis me revient la perte et la douleur,
Ces chagrins que nul remède n'apaise,
Et mes yeux malgré moi sont pleins de larmes
Dont coulents les regrets que je ne puis dire.

Mais c'est alors qu'un rayon d'espérance
Vient éclairer ma nuit, mon désespoir;
En vous, l'ami dont l'amour ne défaut,
Je vois renaître un monde où je respire.

Et tous les deuils qui tourmentaient mon âme
Sont emportés par votre seul amour.
```

## Implementation Details

### Before (Manual String Output)

Printing text character by character:
```lisp
(push 81)(out 0x01)  ; Q
(push 117)(out 0x01) ; u
(push 97)(out 0x01)  ; a
; ... very verbose
```

### After (Using print-rom-string)

Storing strings in ROM and printing efficiently:
```lisp
(data line-1 "Quand ma pensée s'isole en doux silence," 0)
(print-rom-string line-1)
(push 10)(out 0x01)  ; Newline
```

## Efficiency Gain

- **Original approach:** ~3,241 bytes (231 instructions) for 14 lines
- **ROM-based approach:** ~746 bytes (65 instructions)
- **Reduction:** 77% smaller code size

## File Size

- **poem.spl:** 3.3 KB
- **poem.rom:** ~1.2 KB (compiled)

## Learning Value

This project demonstrates:
1. How to use the `(data)` pseudo-instruction
2. The `print-rom-string` instruction for efficient text output
3. Label-based addressing for ROM data
4. Proper null-termination of strings
5. Trade-offs between code clarity and efficiency

## Comparison with Examples

This is larger than typical examples in `examples/` because it includes a complete 14-line poem with meaningful content, making it suitable for a dedicated project file rather than a simple snippet.
