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

## **5.4. Commentaires**

    ; commentaire jusqu'à la fin de la ligne

## **5.5. Fichier SPL**

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
```

*   Toutes les valeurs sont **non signées** (0–255) et les résultats sont **modulo 256**.
*   **Ordre des opérandes** : pour toutes les opérations binaires, le **second élément** (sous le sommet) est l'opérande gauche, le **sommet** est l'opérande droit.
    Ex. `(push 5) (push 3) (sub)` → résultat = `5 - 3 = 2`.
*   `(div)` et `(mod)` : division entière non signée. Division par zéro → **résultat = 0**.
*   `(not)` : **NOT bit‑à‑bit** (inversion des 8 bits, ex. `0x0F` → `0xF0`).

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
| load             | 0x20   | 2 bytes     |
| store            | 0x21   | 2 bytes     |
| jump             | 0x30   | 2 bytes     |
| jump-if-zero     | 0x31   | 2 bytes     |
| jump-if-not-zero | 0x32   | 2 bytes     |
| call             | 0x33   | 2 bytes     |
| return           | 0x34   | 0           |
| in               | 0x40   | 1 byte port |
| out              | 0x41   | 1 byte port |
| label *(pseudo)* | —      | —           |

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
    argument     = number | identifier ;
    number       = hex-number | dec-number ;
    hex-number   = "0x" hex-digit { hex-digit } ;
    dec-number   = digit { digit } ;
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
| 0x3E–0x3F | Réservés              |     | Extensions futures                       |

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

***

# **17. Découverte des capacités (mise à jour)**

`SYSCTL_CAPS` (0xFF) — bits de capabilities :

*   bit0 : **Console status** supporté (`0x02`)
*   bit1 : **Console flush** supporté (`0x03`)
*   bit2 : **RNG8** présent (`0x10`)
*   bit3 : **TIME** présent (`0x11–0x14`)
*   bit4 : **Clavier** présent (`0x20/0x21`)
*   bit5 : **Vidéo** présente (`0x30–0x3D`)
*   bit6 : **Audio** présent (`0x50–0x59`)
*   bit7 : **Souris** présente (`0x70–0x77`)

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