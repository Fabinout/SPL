# **SPL — Structured Parenthesized Language**

### *Spécification Officielle — Version 1.0*


## **📘 Table des matières**

1.  \#1-introduction
2.  \#2-philosophie-du-langage
3.  \#3-aperçu-rapide
4.  \#4-modèle-dexécution
5.  \#5-syntaxe-du-langage
6.  \#6-instructions
7.  \#7-labels-et-résolution
8.  \#8-format-binaire-bytecode-spl
9.  \#9-grammaire-officielle-spl-ebnf
10. \#10-annexes-et-exemples
11. \#11-périphériques-standard-portmapped-io
12. \#12-affichage-vidéo--portmapped-io
13. \#13-audio--portmapped-io
14. \#14-clavier--portmapped-io
15. \#15-souris--portmapped-io
16. \#16-synchronisation--timing
17. \#17-découverte-des-capacités-mise-à-jour
18. \#18-profils-recommandés-pour-la-portabilité
19. \#19-exemples-complets
20. \#20-notes-dimplémentation-vmhôte

***

# **1. Introduction**

SPL (*Structured Parenthesized Language*) est un langage bas-niveau conçu pour être :

*   **facile à générer** par des intelligences artificielles (structure parenthésée)
*   **simple à parser** (S‑expressions strictes)
*   **compact, déterministe** et adapté à une **machine virtuelle minimaliste**

SPL combine la lisibilité d’un langage structuré avec la simplicité d’une **Stack-machine**.

***

# **2. Philosophie du langage**

## **2.1. Structure explicite**

Chaque instruction est une S‑expression :

    (instruction arg1 arg2 ...)

## **2.2. Zéro ambiguïté**

Une seule façon valide d’écrire du SPL (pas de syntaxes alternatives).

## **2.3. Parsing simple**

Grammaire régulière, uniforme, parseur trivial (recursive descent ou stack parser).

## **2.4. Optimisé LLM**

Les modèles modernes gèrent très bien :

*   Parenthèses
*   Formes régulières
*   Noms explicites d’instructions
*   Arguments peu ambigus

***

# **3. Aperçu rapide**

Exemple minimal SPL :

```lisp
(push 0x10)
(push 0x20)
(add)
(store 0x0400)
```

Exemple avec labels :

```lisp
(label start)
(push 1)
(out 0x01)      ; console data
(jump start)
```

***

# **4. Modèle d’exécution**

**VM stack‑based** avec :

*   **Pile de travail** (stack)
*   **Pile de retour** (call/return)
*   **Mémoire linéaire 64 KiB** (adressage 16 bits)
*   **Registres** : `PC`, `SP`, `RP`
*   **Exécution séquentielle** sauf en cas de saut/retour
*   **Terminaison** : l'exécution **s'arrête** (halt) lorsque `PC` dépasse la fin du bytecode, ou lors d'une instruction `(halt)`
*   **Erreurs** (comportement obligatoire) :
    *   Stack underflow (pop sur pile vide) → **halt avec erreur**
    *   Division par zéro (`div`, `mod`) → **résultat = 0** (pas d'exception)
    *   Accès mémoire hors limites (adresse ≥ 0x10000) → **halt avec erreur**
    *   Débordement de pile (work ou return) → **halt avec erreur**
*   **Tailles minimales** :
    *   Pile de travail : au minimum **256 entrées** de 8 bits
    *   Pile de retour : au minimum **64 entrées** de 16 bits (adresses de retour)

> **Endianness** :
>
> *   Les **adresses** codées dans le bytecode sont en **big‑endian** (HI puis LO).
> *   Les opérations `load`/`store` manipulent des **octets** (8 bits).
> *   Les nombres `push` sont **8 bits**.

***

# **5. Syntaxe du langage**

## **5.1. S‑expression**

    (expression) → (identificateur arguments…)

## **5.2. Identificateurs**

*   lettres, chiffres, tirets `-`, underscores `_`
*   sensibles à la casse
*   doivent commencer par une lettre
    Ex. `push`, `jump-if-zero`, `main-loop`, `no_key`

## **5.3. Nombres**

*   décimal : `0`, `42`, `123`
*   hexadécimal : `0x00`, `0x20`, `0xFF`

## **5.4. Chaînes de caractères**

*   Délimitées par des guillemets doubles : `"Hello"`
*   Séquences d'échappement : `\n` (newline), `\t` (tabulation), `\\` (backslash), `\"` (guillemet), `\0` (null)
*   Caractères ASCII uniquement (0–127)
*   Utilisées uniquement comme arguments de `(data ...)`

## **5.5. Commentaires**

    ; commentaire jusqu'à la fin de la ligne

## **5.6. Fichier SPL**

Suite d'expressions séparées par des espaces ou retours à la ligne. **Plusieurs expressions par ligne** sont autorisées. Les commentaires (`;`) s'étendent jusqu'à la fin de la ligne et sont ignorés lors du parsing.

***

# **6. Instructions**

## **6.1. Pile**

```lisp
(push valeur)  ; empile une valeur 8 bits (0–255)
(drop)         ; dépile le sommet (valeur ignorée)
(dup)          ; duplique le sommet : ... a → ... a a
(swap)         ; échange les deux éléments du sommet : ... a b → ... b a
(over)         ; copie le second élément au sommet : ... a b → ... a b a
```

## **6.2. Arithmétique / logiques (8 bits non signés, mod 256)**

```lisp
(add) (sub) (mul) (div) (mod)
(and) (or) (xor) (not)
(lt) (gt)
```

*   Toutes les valeurs sont **non signées** (0–255) et les résultats sont **modulo 256**.
*   **Ordre des opérandes** : pour toutes les opérations binaires, le **second élément** (sous le sommet) est l'opérande gauche, le **sommet** est l'opérande droit.
    Ex. `(push 5) (push 3) (sub)` → résultat = `5 - 3 = 2`.
*   `(div)` et `(mod)` : division entière non signée. Division par zéro → **résultat = 0**.
*   `(not)` : **NOT bit‑à‑bit** (inversion des 8 bits, ex. `0x0F` → `0xF0`).
*   `(lt)` et `(gt)` : comparaison **non signée**. Pop b, pop a ; push **1** si `a < b` (resp. `a > b`), sinon push **0**.

## **6.3. Mémoire**

```lisp
(load adresse16)   ; push mem[addr] sur la pile
(store adresse16)  ; pop sommet → mem[addr]
```

Les adresses sont des **constantes 16 bits** (nombres uniquement, pas de labels) encodées dans l'instruction. Il s'agit d'**adressage direct** uniquement.

## **6.4. Contrôle de flux**

```lisp
(label nom)

(jump nom|addr16)
(jump-if-zero nom|addr16)
(jump-if-not-zero nom|addr16)
(call nom|addr16)
(return)
(halt)
```

*   `(jump)`, `(jump-if-zero)`, `(jump-if-not-zero)`, `(call)` : acceptent un **nom de label** ou une **adresse 16 bits** littérale.
*   `(call)` : empile l'adresse de retour (PC de l'instruction suivante) sur la **pile de retour**, puis saute.
*   `(return)` : dépile une adresse de la **pile de retour** et y saute.
*   `(halt)` : arrête immédiatement l'exécution de la VM.

## **6.5. I/O (Port‑Mapped)**

```lisp
(in port8)    ; push 8 bits depuis le périphérique
(out port8)   ; pop 8 bits vers le périphérique
```

## **6.5.1. String Output from RAM**

```lisp
(print-cstring adresse16)   ; affiche une chaîne null-terminée depuis la RAM
```

*   Lit des octets depuis la **mémoire RAM** à partir de `adresse16` jusqu'à rencontrer un octet nul (`0x00`).
*   Chaque octet non-nul est écrit à la **console** (port `0x01`) automatiquement.
*   L'octet nul (`0x00`) n'est **pas** affiché, c'est le marqueur de fin.
*   L'instruction n'empile ni ne dépile rien sur la pile de travail.
*   Erreur si l'adresse est hors limites de la mémoire (≥ 0x10000).
*   **Cas d'usage** : Afficher du contenu **dynamique** généré à l'exécution.

**Exemple** :
```lisp
; Construire une chaîne à l'exécution
(push 72) (store 0x0400)   ; 'H'
(push 101) (store 0x0401)  ; 'e'
(push 108) (store 0x0402)  ; 'l'
(push 108) (store 0x0403)  ; 'l'
(push 111) (store 0x0404)  ; 'o'
(push 0) (store 0x0405)    ; null terminator
(print-cstring 0x0400)     ; affiche "Hello"
```

## **6.5.2. String Output from Bytecode (ROM)**

```lisp
(print-rom-string adresse16)   ; affiche une chaîne null-terminée depuis le bytecode
```

*   Lit des octets depuis le **bytecode (ROM)** à partir de `adresse16` jusqu'à rencontrer un octet nul (`0x00`).
*   Chaque octet non-nul est écrit à la **console** (port `0x01`) automatiquement.
*   L'octet nul (`0x00`) n'est **pas** affiché, c'est le marqueur de fin.
*   L'instruction n'empile ni ne dépile rien sur la pile de travail.
*   **Cas d'usage** : Afficher du contenu **statique** (poésie, messages constants, documentation).
*   **Avantage** : Plus efficace que `print-cstring` — pas besoin de copier la chaîne en RAM.
*   Erreur si l'adresse est hors limites du bytecode.

**Exemple** :
```lisp
; Chaîne statique dans le bytecode
(data greeting "Hello, World!" 0)

; ... plus tard dans le programme ...
(print-rom-string greeting)  ; affiche "Hello, World!"
```

## **6.6. Données embarquées**

```lisp
(data label octets...)   ; émet des octets bruts dans le bytecode
```

*   Le premier argument est un **nom de label** (obligatoire) qui pointe sur le premier octet émis.
*   Les arguments suivants sont des **nombres 8 bits** (0–255) ou des **chaînes de caractères** (`"texte"`).
*   Chaque nombre émet 1 octet. Chaque caractère d'une chaîne émet 1 octet (ASCII).
*   `(data)` n'émet **aucun opcode** — les octets sont insérés tels quels dans le bytecode.
*   **Attention** : architecture Harvard — les données ROM ne sont pas accessibles par `(load)`/`(store)`. Utiliser `(jump)` pour sauter par-dessus les blocs de données.

**Exemple** :

```lisp
(jump after-msg)
(data msg 72 101 108 108 111)   ; "Hello" en ASCII
(label after-msg)
; msg pointe vers l'offset du 'H' dans le bytecode
```

**Exemple avec chaîne** :

```lisp
(jump after-greeting)
(data greeting "Hello, World!")
(label after-greeting)
```

## **6.7. Macros**

```lisp
(macro nom (instr1 args...)(instr2 args...)...)
```

*   Définit une macro nommée dont le corps est une séquence d'instructions S‑expressions.
*   L'invocation `(nom)` remplace l'appel par le corps de la macro (expansion inline avant assemblage).
*   Les macros peuvent appeler d'autres macros (expansion récursive, profondeur max 64).
*   Le nom d'une macro ne peut pas être un nom d'instruction existant, ni un mot réservé (`label`, `data`, `macro`, `include`).
*   Les noms de macros doivent être **uniques**.
*   Les macros n'acceptent pas d'arguments à l'invocation : `(nom)` uniquement.
*   **Limitation** : si le corps d'une macro contient `(label x)`, invoquer la macro plusieurs fois produit une erreur « duplicate label ».

**Exemple** :

```lisp
(macro print-newline
  (push 10)(out 0x01))

(macro print-A
  (push 65)(out 0x01))

(print-A)
(print-newline)
(halt)
; Sortie : "A\n"
```

## **6.8. Inclusion de fichiers**

```lisp
(include "chemin/vers/fichier.spl")
```

*   Insère le contenu du fichier spécifié à la position de la directive, avant le parsing.
*   Le chemin est résolu **relativement au fichier contenant la directive** `include`.
*   Les inclusions récursives sont supportées (un fichier inclus peut inclure d'autres fichiers).
*   Les inclusions **circulaires** sont détectées et produisent une erreur.

**Exemple** :

```lisp
; --- lib.spl ---
(macro emit-hello
  (push 72)(out 0x01)   ; H
  (push 105)(out 0x01)) ; i

; --- main.spl ---
(include "lib.spl")
(emit-hello)
(halt)
; Sortie : "Hi"
```

***

# **7. Labels et résolution**

    (label boucle)

*   Les labels se résolvent en **adresses 16 bits (offset en octets dans le bytecode)** à l'assemblage.
*   Les **références avant** (forward references) sont autorisées : un label peut être utilisé avant d'être défini.
*   Les noms de labels doivent être **uniques** dans un fichier SPL.
*   `(label)` n'émet **aucun octet** dans le bytecode — aucun coût d'exécution.

***

# **8. Format binaire (bytecode SPL)**

Chaque instruction s’encode :

    [ opcode : 1 octet ][ args : n octets ]

## **8.1. Table des opcodes**

| Instruction      | Opcode | Args        |
| ---------------- | ------ | ----------- |
| halt             | 0x00   | 0           |
| push             | 0x01   | 1 byte      |
| drop             | 0x02   | 0           |
| dup              | 0x03   | 0           |
| swap             | 0x04   | 0           |
| over             | 0x05   | 0           |
| add              | 0x10   | 0           |
| sub              | 0x11   | 0           |
| mul              | 0x12   | 0           |
| div              | 0x13   | 0           |
| mod              | 0x14   | 0           |
| and              | 0x15   | 0           |
| or               | 0x16   | 0           |
| xor              | 0x17   | 0           |
| not              | 0x18   | 0           |
| lt               | 0x19   | 0           |
| gt               | 0x1A   | 0           |
| load             | 0x20   | 2 bytes     |
| store            | 0x21   | 2 bytes     |
| print-cstring    | 0x42   | 2 bytes     |
| print-rom-string | 0x43   | 2 bytes     |
| jump             | 0x30   | 2 bytes     |
| jump-if-zero     | 0x31   | 2 bytes     |
| jump-if-not-zero | 0x32   | 2 bytes     |
| call             | 0x33   | 2 bytes     |
| return           | 0x34   | 0           |
| in               | 0x40   | 1 byte port |
| out              | 0x41   | 1 byte port |
| label *(pseudo)* | —      | —           |
| data *(pseudo)*  | —      | n bytes     |

> **Adresses (2 bytes)** : **big‑endian** (HI, LO).  
> **Ports** : 8 bits (0x00–0xFF).

## **8.2. Exemple d’encodage**

SPL :

```lisp
(push 0x10)
(push 0x20)
(add)
(store 0x0400)
```

Bytecode :

    01 10
    01 20
    10
    21 04 00

***

# **9. Grammaire officielle SPL (EBNF)**

    program      = { expression | comment } ;
    expression   = "(" identifier { argument } ")" ;
    identifier   = letter { letter | digit | "-" | "_" } ;
    argument     = number | identifier | string ;
    number       = hex-number | dec-number ;
    hex-number   = "0x" hex-digit { hex-digit } ;
    dec-number   = digit { digit } ;
    string       = '"' { string-char | escape-seq } '"' ;
    string-char  = any-ascii-except-quote-backslash-newline ;
    escape-seq   = "\" ( "n" | "t" | "\" | '"' | "0" ) ;
    comment      = ";" { any-char-except-newline } newline ;
    letter       = "a"…"z" | "A"…"Z" ;
    digit        = "0"…"9" ;
    hex-digit    = digit | "a"…"f" | "A"…"F" ;

> Les tokens sont séparés par un ou plusieurs caractères d'espacement (espace, tabulation, retour à la ligne). Les commentaires sont ignorés lors du parsing.

***

# **10. Annexes et exemples**

## **10.1. Boucle infinie**

```lisp
(label loop)
(push 1)
(out 0x01)
(jump loop)
```

## **10.2. Appel de fonction**

```lisp
(call init)
(push 42)
(out 0x01)
(halt)

(label init)
(push 0xFF)
(out 0x01)
(return)
```

***

# **11. Périphériques standard (Port‑Mapped I/O)**

## **11.1. Espace des ports**

*   Taille : **8 bits** (`0x00–0xFF`)
*   Réservations :
    *   `0x00–0x1F` : **Core I/O (obligatoire)**
    *   `0x20–0x7F` : Extensions standard (optionnelles)
    *   `0x80–0xFE` : Périphériques spécifiques à l’implémentation
    *   `0xFF` : **SYSCTL** (capabilities/features)

Un programme portable s’appuie sur **Core I/O** et **vérifie les capacités** pour les extensions.

## **11.2. Core I/O (obligatoire)**

### 11.2.1. Console (sortie texte)

*   `0x01` — **CONSOLE\_DATA (W)** : `(out 0x01)` envoie l’octet dépilé à la console.  
    Encodage recommandé : **UTF‑8 pass‑through** (ASCII trivial).
*   `0x02` — **CONSOLE\_STATUS (R)** : `(in 0x02)` lit l’état (bit0 = prêt).  
    Profil simple : **toujours 1**.
*   `0x03` — **CONSOLE\_FLUSH (W, optionnel)** : `(out 0x03)` demande un flush.

**Politique de blocage**

*   **Profil A (par défaut)** : `out(0x01)` ne bloque pas ; l’hôte bufferise et flush sur `\n` ou périodiquement.
*   **Profil B (non‑bloquant)** : `out(0x01)` **peut ignorer** si `STATUS&1==0` (le code doit tester le status).

**Exemple (imprimer “A\n”)**

```lisp
(push 65) (out 0x01)
(push 10) (out 0x01)
```

### 11.2.2. RNG (aléatoire)

*   `0x10` — **RNG8 (R)** : `(in 0x10)` pousse un octet pseudo‑aléatoire.  
    Si non supporté : peut retourner 0.

### 11.2.3. SYSCTL\_CAPS

*   `0xFF` — **SYSCTL\_CAPS (R)** : octet de **capabilities** (voir Chap. 17).

## **11.3. Extensions Core recommandées**

*   **Temps** :
    *   `0x11` — **TIME\_MS\_B0 (R)** : octet 0 (bits 0–7, poids faible)
    *   `0x12` — **TIME\_MS\_B1 (R)** : octet 1 (bits 8–15)
    *   `0x13` — **TIME\_MS\_B2 (R)** : octet 2 (bits 16–23)
    *   `0x14` — **TIME\_MS\_B3 (R)** : octet 3 (bits 24–31, poids fort)
        → compteur monotone **32 bits** (millisecondes). La lecture de `B3` (0x14) **verrouille** (latch) la valeur complète ; lire ensuite `B2`, `B1`, `B0` pour obtenir un snapshot atomique.

***

# **12. Affichage (Vidéo) — Port‑Mapped I/O**

## **12.1. Objectifs**

*   Profil minimal portable **framebuffer** (8 bpp et 16 bpp).
*   Interface simple, *stateless* côté VM (polling).

## **12.2. Ports vidéo (réservé 0x30–0x3F)**

|      Port | Nom                   | R/W | Description                              |
| --------: | --------------------- | --- | ---------------------------------------- |
|      0x30 | VID\_MODE             | W   | 0=off, **1=FB8**, **2=FB16**             |
|      0x31 | VID\_RES\_W\_LO       | W   | Largeur LO                               |
|      0x32 | VID\_RES\_W\_HI       | W   | Largeur HI                               |
|      0x33 | VID\_RES\_H\_LO       | W   | Hauteur LO                               |
|      0x34 | VID\_RES\_H\_HI       | W   | Hauteur HI                               |
|      0x35 | VID\_STRIDE\_LO       | W   | Octets/ligne LO                          |
|      0x36 | VID\_STRIDE\_HI       | W   | Octets/ligne HI                          |
|      0x37 | VID\_FB\_ADDR\_LO     | W   | Adresse FB LO                            |
|      0x38 | VID\_FB\_ADDR\_HI     | W   | Adresse FB HI                            |
|      0x39 | VID\_STATUS           | R   | bit0: vblank, bit1: fb-ready (impl‑déf.) |
|      0x3A | VID\_FLIP             | W   | Flip/commit (octet ignoré)               |
|      0x3B | VID\_CLEAR\_COLOR\_LO | W   | Couleur LO                               |
|      0x3C | VID\_CLEAR\_COLOR\_HI | W   | Couleur HI                               |
|      0x3D | VID\_CLEAR            | W   | Clear écran (octet ignoré)               |
| 0x3E | RECT_EXEC             | W   | Exécute rectangle fill (octet ignoré)    |
| 0x3F | LINE_EXEC             | W   | Exécute line draw (octet ignoré)         |

**FB8** : 1 octet/pixel, palette **implémentation‑définie** (recommandé : **grayscale**).
**FB16** : RGB565 (2 octets/pixel, en RAM **LO puis HI** pour chaque pixel).

## **12.3. Séquence d’initialisation**

1.  `VID_MODE`
2.  `VID_RES_*`, `VID_STRIDE_*`
3.  `VID_FB_ADDR_*`
4.  Optionnel : `VID_CLEAR_COLOR_*`, `VID_CLEAR`
5.  `VID_FLIP`

## **12.4. Convention de mémoire**

*   Adresse FB = `FB = HI<<8 | LO`
*   Offset pixel FB8 : `FB + y*stride + x`
*   Offset pixel FB16 : `FB + y*stride + 2*x` (LO, puis HI)

## **12.5. Exemple (320×240, FB8, fb=0x8000)**

```lisp
(push 1)      (out 0x30)     ; FB8
(push 0x40)   (out 0x31)     ; W_LO = 320
(push 0x01)   (out 0x32)     ; W_HI
(push 0xF0)   (out 0x33)     ; H_LO = 240
(push 0x00)   (out 0x34)     ; H_HI
(push 0x40)   (out 0x35)     ; STRIDE_LO = 320
(push 0x01)   (out 0x36)     ; STRIDE_HI
(push 0x00)   (out 0x37)     ; FB_LO = 0x00
(push 0x80)   (out 0x38)     ; FB_HI = 0x80
(push 0x00)   (out 0x3B)     ; clear color = 0
(push 0x00)   (out 0x3C)
(push 1)      (out 0x3D)     ; clear
(push 1)      (out 0x3A)     ; flip
```

## **12.6. Primitives graphiques (Drawing) — Port‑Mapped I/O**

### 12.6.1. Modèle

Les primitives graphiques utilisent une **zone mémoire partagée** pour les paramètres, puis des **ports pour déclencher l'exécution**.

**Buffer de paramètres** (adresses `0x0000–0x0009` de la mémoire RAM):

| Offset | Nom            | Description                           |
| -----: | -------------- | ------------------------------------- |
| 0x0000 | DRAW\_X\_LO    | Coordonnée X (16-bit, octet 0)        |
| 0x0001 | DRAW\_X\_HI    | Coordonnée X (16-bit, octet 1)        |
| 0x0002 | DRAW\_Y\_LO    | Coordonnée Y (16-bit, octet 0)        |
| 0x0003 | DRAW\_Y\_HI    | Coordonnée Y (16-bit, octet 1)        |
| 0x0004 | DRAW\_W\_LO    | Largeur (16-bit, octet 0)             |
| 0x0005 | DRAW\_W\_HI    | Largeur (16-bit, octet 1)             |
| 0x0006 | DRAW\_H\_LO    | Hauteur (16-bit, octet 0)             |
| 0x0007 | DRAW\_H\_HI    | Hauteur (16-bit, octet 1)             |
| 0x0008 | DRAW\_COLOR\_LO | Couleur (16-bit, octet 0, FB16/FB8)   |
| 0x0009 | DRAW\_COLOR\_HI | Couleur (16-bit, octet 1)             |

### 12.6.2. Rectangle fill

Remplit un rectangle plein de la couleur spécifiée.

**Séquence :**

1. Initialiser la vidéo (`VID_MODE`, `VID_RES_*`, etc.)
2. Écrire `X`, `Y`, `W`, `H`, `Color` dans le buffer (`0x0000–0x0009`)
3. Écrire n'importe quelle valeur à port `0x3E`

**Paramètres :**

*   **X, Y** : coordonnées top-left du rectangle (16-bit, clippées à la résolution)
*   **W, H** : largeur et hauteur en pixels (16-bit)
*   **Color** : couleur (même format que la vidéo : 0–255 en FB8, RGB565 en FB16)

**Notes :**

*   Les rectang​les complètement hors-écran ne sont pas dessinés.
*   Les rectangles partiellement hors-écran sont clippés.

**Exemple (FB8, 320×240) :**

```lisp
; Rectangle blanc (255) à (50, 50), 100×100 pixels
(push 50)   (store 0x0000)   ; X_LO = 50
(push 0)    (store 0x0001)   ; X_HI = 0
(push 50)   (store 0x0002)   ; Y_LO = 50
(push 0)    (store 0x0003)   ; Y_HI = 0
(push 100)  (store 0x0004)   ; W_LO = 100
(push 0)    (store 0x0005)   ; W_HI = 0
(push 100)  (store 0x0006)   ; H_LO = 100
(push 0)    (store 0x0007)   ; H_HI = 0
(push 255)  (store 0x0008)   ; Color = 255 (blanc)
(push 0)    (store 0x0009)   ; Color HI = 0
(push 1)    (out 0x3E)       ; Execute rectangle
```

### 12.6.3. Line drawing (Bresenham)

Dessine une ligne entre deux points avec l'**algorithme Bresenham**.

**Séquence :**

1. Écrire `X0`, `Y0`, `X1`, `Y1`, `Color` dans le buffer
2. Écrire n'importe quelle valeur à port `0x3F`

**Paramètres :**

*   **X0, Y0** : point de départ (16-bit, bits 0–1)
*   **X1, Y1** : point d'arrivée (16-bit, bits 4–7)
*   **Color** : couleur

**Notes :**

*   Ligne **semi-ouverte** : inclut le point start, exclut le point end.
*   Clipping automatique aux limites de l'écran.
*   Optimisé pour lignes longues.

**Exemple :**

```lisp
; Ligne diagonale de (10, 10) à (100, 100) en blanc
(push 10)   (store 0x0000)   ; X0 = 10
(push 0)    (store 0x0001)   ; X0_HI = 0
(push 10)   (store 0x0002)   ; Y0 = 10
(push 0)    (store 0x0003)   ; Y0_HI = 0
(push 100)  (store 0x0004)   ; X1 = 100
(push 0)    (store 0x0005)   ; X1_HI = 0
(push 100)  (store 0x0006)   ; Y1 = 100
(push 0)    (store 0x0007)   ; Y1_HI = 0
(push 255)  (store 0x0008)   ; Color = 255
(push 0)    (store 0x0009)
(push 1)    (out 0x3F)       ; Execute line
```

## **12.7. Dessin et géométrie — Patterns recommandés**

Cette section documente les **patterns courants** pour implémenter des primitives de dessin sans opcodes dédiés (approche software, ou complément aux ports 0x3E/0x3F).

### 12.7.1. Dessiner un point (pixel)

**Pattern :**

```lisp
; Paramètres (passer en arguments ou charger depuis RAM)
; x = 0 à 159 (160×120)
; y = 0 à 119
; framebuffer base = 0x8000
; color = 0xFF (blanc) ou 0x00 (noir)

; Adresse = framebuffer_base + y * 160 + x
(push 0x80)        ; FB base HI
(push 0x00)        ; FB base LO
(push y_value)     ; charger Y
(push 160)
(mul)              ; Y * 160
(add)              ; base + Y*160
(push x_value)     ; charger X
(add)              ; + X
(push 0xFF)        ; couleur (blanc)
(store addr)       ; pixel[x,y] = 0xFF
```

### 12.7.2. Dessiner un rectangle rempli (boucles imbriquées)

**Pattern (sans utiliser port 0x3E) :**

```lisp
; Paramètres
; x, y = coin supérieur gauche
; w, h = largeur, hauteur
; color = 0xFF ou 0x00

(label rect-fill)
  ; y-loop
  (push y_top)
  (label rect-y-loop)
  (push y_bottom) (over) (swap) (lt)
  (jump-if-zero rect-y-end)

    ; x-loop
    (push x_left)
    (label rect-x-loop)
    (push x_right) (over) (swap) (lt)
    (jump-if-zero rect-x-end)

      ; Dessiner pixel[x, y]
      ; addr = 0x8000 + y * 160 + x
      (push 0x8000)
      (over)  ; y
      (push 160) (mul) (add)
      (swap)  ; x
      (add)
      (push 0xFF) (store addr)  ; pixel = blanc

      (push 1) (add)  ; x++
    (jump rect-x-loop)
    (label rect-x-end)
    (drop)  ; nettoyer x

    (push 1) (add)  ; y++
  (jump rect-y-loop)
  (label rect-y-end)
  (drop)  ; nettoyer y
```

**Simplifié (avec 2 boucles) :**

```lisp
(macro draw-filled-rect (x y width height color)
  ; Boucle y
  (push 0)
  (label rect-y)
  (dup) (push height) (lt)
  (jump-if-not-zero rect-y-body)
  (jump rect-y-end)
  (label rect-y-body)
    ; Boucle x
    (push 0)
    (label rect-x)
    (dup) (push width) (lt)
    (jump-if-not-zero rect-x-body)
    (jump rect-x-end)
    (label rect-x-body)
      ; Calculer offset = y*160 + x + fb_base
      ; (écrire pixel)
      (push 1) (add)  ; x++
    (jump rect-x)
    (label rect-x-end)
    (drop)
    (push 1) (add)  ; y++
  (jump rect-y)
  (label rect-y-end)
  (drop)
)
```

### 12.7.3. Détection collision rectangle-rectangle

**Algorithme AABB (Axis-Aligned Bounding Box) :**

Deux rectangles **r1** et **r2** se chevauchent si et seulement si :

```
r1.x1 < r2.x2  AND  r1.x2 > r2.x1  AND
r1.y1 < r2.y2  AND  r1.y2 > r2.y1
```

**Pattern SPL :**

```lisp
; Paramètres (charger en stack ou RAM)
; r1: x1, y1, x2, y2 (coin haut-gauche et bas-droit)
; r2: x1, y1, x2, y2

(macro check-collision-aabb (r1x1 r1y1 r1x2 r1y2 r2x1 r2y1 r2x2 r2y2)
  ; r1.x1 < r2.x2 ?
  (push r1x1) (push r2x2) (lt)
  (jump-if-zero no-collision)

  ; r1.x2 > r2.x1 ?
  (push r1x2) (push r2x1) (gt)
  (jump-if-zero no-collision)

  ; r1.y1 < r2.y2 ?
  (push r1y1) (push r2y2) (lt)
  (jump-if-zero no-collision)

  ; r1.y2 > r2.y1 ?
  (push r1y2) (push r2y1) (gt)
  (jump-if-zero no-collision)

  ; Collision détectée
  (push 1) (jump collision-end)
  (label no-collision)
  (push 0)
  (label collision-end)
)
```

**Résultat :** 1 = collision, 0 = pas de collision.

### 12.7.4. Exemple : Pong (déplacer une palette)

```lisp
; Initialiser paddle
(push 75)      (store 0xFFC0)  ; paddle_x
(push 50)      (store 0xFFC1)  ; paddle_y
(push 10)      (store 0xFFC2)  ; paddle_w
(push 30)      (store 0xFFC3)  ; paddle_h
(push 3)       (store 0xFFC4)  ; paddle speed

(label game-loop)

; Lire touches et déplacer
(in 0x24)  ; UP ?
(jump-if-zero skip-move-up)
  (load 0xFFC1) (push 3) (sub) (store 0xFFC1)  ; y -= 3
(label skip-move-up)

(in 0x25)  ; DOWN ?
(jump-if-zero skip-move-down)
  (load 0xFFC1) (push 3) (add) (store 0xFFC1)  ; y += 3
(label skip-move-down)

; Effacer ancienne paddle (remplir avec noir)
(load 0xFFC0) (load 0xFFC1)
(load 0xFFC2) (load 0xFFC3)
; ... dessiner rectangle noir ...

; Redessiner paddle (blanc)
(load 0xFFC0) (load 0xFFC1)
(load 0xFFC2) (load 0xFFC3)
; ... dessiner rectangle blanc ...

; Attendre frame (~16ms)
; ...

(jump game-loop)
```

**Notes :**

*   Ces patterns sont **optimisables** pour une VM réelle (boucles non-déroulées, registres, etc.)
*   **Macros recommandées** pour Pong :
    - `(draw-rect x y w h color)` → déplier en boucles imbriquées
    - `(draw-pixel x y color)` → calcul direct d'adresse
    - `(check-aabb r1 r2)` → comparaisons AABB
*   **Framebuffer** : accès direct en RAM (pas de port spécialisé nécessaire)

***

# **13. Audio — Port‑Mapped I/O**

## **13.1. Objectifs**

*   **PSG 4 canaux** (fréquence 16 bits, volume 0..15, forme d’onde simple, gate).
*   **FIFO PCM 8‑bit** optionnelle.

## **13.2. Ports audio (0x50–0x59)**

| Port | Nom              | R/W | Description                                 |
| ---: | ---------------- | --- | ------------------------------------------- |
| 0x50 | AUD\_CH\_SELECT  | W   | Canal actif (0..3)                          |
| 0x51 | AUD\_FREQ\_LO    | W   | Fréquence LO                                |
| 0x52 | AUD\_FREQ\_HI    | W   | Fréquence HI                                |
| 0x53 | AUD\_VOLUME      | W   | 0..15                                       |
| 0x54 | AUD\_WAVEFORM    | W   | 0=sine,1=square,2=tri,3=saw,4=noise         |
| 0x55 | AUD\_GATE        | W   | 0=off, 1=on                                 |
| 0x56 | AUD\_STATUS      | R   | bit0: engine on, bit1: PCM FIFO dispo       |
| 0x57 | AUD\_MASTER\_VOL | W   | 0..15                                       |
| 0x58 | PCM\_DATA        | W   | Écrit 1 octet audio dans FIFO (si présente) |
| 0x59 | PCM\_STATUS      | R   | bit0: FIFO non‑pleine, bit1: non‑vide       |

> **Fréquence** : valeur entière, facteur d’échelle **K=1 Hz** (par défaut).  
> Les hôtes peuvent approximer/quantifier.

**Exemple : bip 440 Hz canal 0**

```lisp
(push 0)    (out 0x50)  ; canal 0
(push 0xB8) (out 0x51)  ; 440 = 0x01B8
(push 0x01) (out 0x52)
(push 8)    (out 0x53)
(push 1)    (out 0x54)  ; carré
(push 1)    (out 0x55)  ; gate on
; ... plus tard ...
(push 0)    (out 0x55)  ; gate off
```

***

# **14. Clavier — Port‑Mapped I/O**

## **14.1. Modèle**

*   **Scancodes 8 bits** (recommandation : ASCII pour alphanum + codes spéciaux pour touches non ASCII).
*   File **non bloquante**.

## **14.2. Ports clavier (0x20–0x23)**

| Port | Nom         | R/W | Description                                |
| ---: | ----------- | --- | ------------------------------------------ |
| 0x20 | KBD\_DATA   | R   | Lit un octet (touche)                      |
| 0x21 | KBD\_STATUS | R   | bit0: data ready                           |
| 0x22 | KBD\_MODS   | R   | bit0=Shift,1=Ctrl,2=Alt,3=Meta (optionnel) |
| 0x23 | KBD\_CLEAR  | W   | Vide la file (octet ignoré)                |

**Lire si une touche est dispo :**

```lisp
(in 0x21) (push 1) (and)
(jump-if-zero no_key)
(in 0x20)            ; -> code sur la pile
; ... traiter ...
(label no_key)
```

## **14.3. Ports clavier polling d'état (optionnel, 0x24–0x27)**

**Profil simplifié pour les jeux temps réel** (ex. : Pong, shoot-em-up).

Modèle **polling non-destructif** : chaque lecture retourne l'état **courant** de la touche (1 = enfoncée, 0 = relâchée).

| Port | Nom            | R/W | Description                           |
|------|----------------|-----|---------------------------------------|
| 0x24 | KBD\_KEY\_UP   | R   | 1 si touche UP enfoncée, 0 sinon      |
| 0x25 | KBD\_KEY\_DOWN | R   | 1 si touche DOWN enfoncée, 0 sinon    |
| 0x26 | KBD\_KEY\_LEFT | R   | 1 si touche LEFT enfoncée, 0 sinon    |
| 0x27 | KBD\_KEY\_RIGHT| R   | 1 si touche RIGHT enfoncée, 0 sinon   |

**Mappage clavier recommandé :**

*   UP = Flèche Haut (↑) ou W
*   DOWN = Flèche Bas (↓) ou S
*   LEFT = Flèche Gauche (←) ou A
*   RIGHT = Flèche Droite (→) ou D

**Exemple (déplacer palette) :**

```lisp
(label update-paddle)
(in 0x24)                    ; lire UP
(jump-if-zero check_down)
  ; ... déplacer palette vers le haut ...
(label check_down)
(in 0x25)                    ; lire DOWN
(jump-if-zero update-done)
  ; ... déplacer palette vers le bas ...
(label update-done)
```

**Notes :**

*   Complément au modèle **KBD_DATA/STATUS** (0x20-0x23) orienté événements.
*   Permet un gameplay fluide sans file d'attente.
*   Si implémenté, les ports 0x24-0x27 retournent **0** si la touche est absente (ex. : clavier virtuel sans tous les modifieurs).

***

# **15. Souris — Port‑Mapped I/O**

## **15.1. Modèle**

*   Position **absolue** X/Y sur 16 bits.
*   **Boutons** : bit0=L, bit1=R, bit2=M.
*   **Molette** : relatif **signé** 8 bits en complément à deux (−128..+127, réarmé à 0 après lecture). C'est la seule valeur signée de la spécification.

## **15.2. Ports souris (0x70–0x77)**

| Port | Nom            | R/W | Description                           |
| ---: | -------------- | --- | ------------------------------------- |
| 0x70 | MOUSE\_X\_LO   | R   | X LO                                  |
| 0x71 | MOUSE\_X\_HI   | R   | X HI                                  |
| 0x72 | MOUSE\_Y\_LO   | R   | Y LO                                  |
| 0x73 | MOUSE\_Y\_HI   | R   | Y HI                                  |
| 0x74 | MOUSE\_BUTTONS | R   | bits 0..2                             |
| 0x75 | MOUSE\_WHEEL   | R   | int8 relatif                          |
| 0x76 | MOUSE\_STATUS  | R   | bit0: présent, bit1: mouvement récent |
| 0x77 | MOUSE\_CLEAR   | W   | Réarme (octet ignoré)                 |

***

# **16. Synchronisation & Timing**

## **16.1. VBlank / VSync (vidéo)**

*   `VID_STATUS` (0x39) bit0 = 1 pendant **vblank** (implémentation).
*   Recommandé d’attendre vblank avant `VID_FLIP`.

**Attente vblank :**

```lisp
(label wait_vb)
(in 0x39)
(push 1) (and)
(jump-if-zero wait_vb)
(push 1) (out 0x3A) ; flip
```

## **16.2. Timer (extensions Core)**

*   Ports `0x11`–`0x14` (`TIME_MS_B0`–`TIME_MS_B3`) → compteur 32 bits (ms).
*   **Ordre de lecture** : lire `B3` (0x14) en premier pour verrouiller la valeur, puis `B2` (0x13), `B1` (0x12), `B0` (0x11).

**Synchronisation 60 FPS :**

60 FPS = 1 frame par ~16.67 ms (arrondi à 16–17 ms).

**Pattern recommandé (sans attente active) :**

```lisp
(label main-loop)

; === LOGIQUE DU JEU ===
; (déplacer entités, détecter collisions, dessiner)

; === ATTENDRE FRAME ===
; Boucle d'attente grossière (~16.67 ms)
; Ajuster la constante selon la vitesse de la VM
(push 0)
(label delay-loop)
(push 1) (add)
(push 100) (dup) (swap) (lt)  ; 100 itérations = ~16-20 ms (impl-dépendant)
(jump-if-not-zero delay-loop)
(drop)

(jump main-loop)
```

**Pattern recommandé (avec timer) :**

```lisp
; Lire timestamp initial
(in 0x14) (drop)     ; latch
(in 0x13)            ; B2
(store 0xFFFE)       ; sauvegarder en RAM

(label main-loop)

; === LOGIQUE ===
; ...

; === ATTENDRE JUSQU'À 16ms ÉCOULÉS ===
(label wait-frame)
(in 0x14) (drop)     ; latch courant
(in 0x13)            ; B2 courant
(load 0xFFFE)        ; charger B2 précédent
(sub)                ; diff = courant - ancien
(push 16) (lt)       ; diff < 16 ?
(jump-if-not-zero wait-frame)  ; boucler si pas assez de temps

; Sauvegarder nouveau timestamp
(in 0x14) (drop)
(in 0x13)
(store 0xFFFE)

(jump main-loop)
```

**Notes :**

*   La **granularité en ms** rend 16.67 ms impossible à atteindre exactement (arrondir à 16 ou 17).
*   Lecture incomplète du timer : si seul `B1` ou `B2` est nécessaire, lire `B3` en premier (latch) reste obligatoire.
*   **Overflow** : 32-bit ms = ≈49 jours. Pas d'enjeu pour la plupart des jeux.

***

# **17. Découverte des capacités (mise à jour)**

`SYSCTL_CAPS` (0xFF) — bits de capabilities :

*   bit0 : **Console status** supporté (`0x02`)
*   bit1 : **Console flush** supporté (`0x03`)
*   bit2 : **RNG8** présent (`0x10`)
*   bit3 : **TIME** présent (`0x11–0x14`)
*   bit4 : **Clavier (événements)** présent (`0x20/0x21`)
*   bit5 : **Vidéo** présente (`0x30–0x3D` + optionnel `0x3E–0x3F` primitives graphiques)
*   bit6 : **Audio** présent (`0x50–0x59`)
*   bit7 : **Souris** présente (`0x70–0x77`)

**Extensions optionnelles (pas de bit dédié) :**

*   **Clavier polling d'état** (`0x24–0x27`) : indépendant ; si bit4 = 1, le clavier est présent (soit mode événements, soit polling, soit les deux)
*   **Primitives graphiques** (`0x3E–0x3F`) : implicite si bit5 (vidéo) = 1 sur les hôtes supportant FB8/FB16 avec dessin hardware

**Exemple : tester vidéo**

```lisp
(in 0xFF)
(push 0x20) (and)         ; bit5 ?
(jump-if-zero no_video)
; ... init vidéo ...
(label no_video)
```

***

# **18. Profils recommandés (pour la portabilité)**

## **18.1. SPL‑Core‑Console (obligatoire)**

*   Console : `0x01` (data), `0x02` (status facultatif), `0x03` (flush optionnel).
*   RNG (0x10) : facultatif → peut renvoyer 0.
*   SYSCTL\_CAPS (0xFF) : présent.

## **18.2. SPL‑FB8‑320x240 (optionnel standard)**

*   Vidéo : FB8, **320×240**, stride=320, framebuffer configurable.
*   Support `VID_STATUS`, `VID_FLIP`.

## **18.3. SPL‑Audio‑PSG4 (optionnel standard)**

*   4 canaux, waveforms {sine,square,tri,saw,noise}, volume 0..15, gate.

## **18.4. SPL‑Input‑KB+Mouse (optionnel standard)**

*   Clavier (0x20/0x21), Souris (0x70–0x77).

## **18.5. SPL‑Pong‑Minimal (profil de jeu 2D simple)**

**Cas d'usage :** jeux arcade minimalistes (Pong, Breakout, shoot-em-up simple).

**Composants requis :**

*   **Console** : `0x01` (sortie debug/log)
*   **Vidéo** : FB8, **160×120**, `0x30–0x3A`, optionnel primitives `0x3E–0x3F`
*   **Clavier** : polling d'état `0x24–0x27` (UP/DOWN/LEFT/RIGHT)
*   **Timer** : `0x11–0x14` (synchronisation 60 FPS)
*   **RNG** : `0x10` (optionnel, pour IA/variations)

**Exemple d'initialisation minimale :**

```lisp
; Init vidéo 160×120
(push 1)      (out 0x30)   ; VID_MODE = FB8
(push 160)    (out 0x31)   ; W_LO
(push 0)      (out 0x32)   ; W_HI
(push 120)    (out 0x33)   ; H_LO
(push 0)      (out 0x34)   ; H_HI
(push 160)    (out 0x35)   ; STRIDE_LO
(push 0)      (out 0x36)   ; STRIDE_HI
(push 0)      (out 0x37)   ; FB_LO = 0x8000
(push 128)    (out 0x38)   ; FB_HI

; Effacer l'écran
(push 0)      (out 0x3B)   ; CLEAR_COLOR = 0
(push 1)      (out 0x3D)   ; CLEAR
(push 1)      (out 0x3A)   ; FLIP

; Prêt à dessiner
```

**Mémoire recommandée :**

*   `0x0000–0x007F` : zone de travail (variables locales)
*   `0x0080–0x7FFF` : code + données
*   `0x8000–0xFFFF` : framebuffer 160×120 (19200 octets utilisés)

**Performances attendues :**

*   ~60 FPS sur une VM moderne
*   Temps logique : < 15 ms par frame
*   Dessin : via `store` direct (pas de primitives hardware) ou via `0x3E` si disponible

***

# **19. Exemples complets**

## **19.1. “Hello, vidéo” (FB8 160×120)**

```lisp
; Init FB8 160x120, stride=160, fb=0x8000
(push 1)    (out 0x30)
(push 0xA0) (out 0x31)   ; 160
(push 0x00) (out 0x32)
(push 0x78) (out 0x33)   ; 120
(push 0x00) (out 0x34)
(push 0xA0) (out 0x35)   ; stride 160
(push 0x00) (out 0x36)
(push 0x00) (out 0x37)   ; fb 0x8000
(push 0x80) (out 0x38)
(push 0x20) (out 0x3B)   ; clear color = 32
(push 1)    (out 0x3D)   ; clear
(push 1)    (out 0x3A)   ; flip
```

## **19.2. “Bip si touche pressée”**

```lisp
(label loop)
(in 0x21) (push 1) (and)      ; key ready ?
(jump-if-zero loop)
(in 0x20)                      ; lit la touche (pas utilisée ici)
(push 0) (out 0x50)           ; ch 0
(push 0x40) (out 0x51)        ; ~0x0400 Hz
(push 0x04) (out 0x52)
(push 10)  (out 0x53)
(push 1)   (out 0x54)         ; square
(push 1)   (out 0x55)         ; gate on
; ... temporisation ...
(push 0)   (out 0x55)         ; gate off
(jump loop)
```

## **19.3. “Écho clavier → console”**

```lisp
(label main)
(in 0x21) (push 1) (and)
(jump-if-zero main)
(in 0x20)          ; code touche
(dup)
(out 0x01)         ; afficher
(push 10)
(out 0x01)         ; newline
(jump main)
```

***

# **20. Notes d’implémentation (VM/hôte)**

*   **Console** : bufferiser et **flusher** sur `\n` ; `(out 0x03)` déclenche un flush immédiat si supporté.
*   **Vidéo** : mapper le **framebuffer** RAM vers une surface (ex. SDL).
    *   **FB8** : palette par défaut = **grayscale** (index n → (n,n,n)).
    *   **Flip** : copie/présentation de la surface affichée.
*   **Audio** : synthèse **PSG** en temps réel, mix des 4 canaux ; **PCM** FIFO optionnelle.
*   **Clavier/souris** : l’hôte alimente des registres/queues lus par `in`.
*   **Timing** : si pas de vsync réelle, `VID_STATUS` peut toujours annoncer “prêt”.

***

## **Appendice : Outils de la toolchain (référence)**

### Assembleur SPL de référence

Un assembleur Python minimal (deux passes) a été fourni séparément.

*   Entrée : `.spl`
*   Sortie : bytecode `.rom`
*   Résolution de labels, encodage big‑endian pour adresses 16 bits.
*   Ports et périphériques sont exprimés en **nombres** (`0xNN`) dans `(in/out)`.

### Disassembleur / VM

*   Un **disassembleur** et une **VM de référence** (C/Rust/Python) sont recommandés pour valider les profils **Core** et **Extensions**.

***

## **Fin de la spécification SPL 1.0**