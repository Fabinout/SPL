# Phase 1 : Spécification des ports pour Pong — Analyse et Recommandations

**Date :** 2026-02-14
**Objectif :** Evaluer et clarifier la spécification SPL pour le cas d'usage Pong

---

## T1.1 — Spécifier le port vidéo pour Pong

### 📋 Analyse de la spécification existante

La spécification SPL (section 12, "Affichage (Vidéo) — Port-Mapped I/O") définit déjà un système complet de ports vidéo (0x30-0x3F) supportant :
- **FB8** (8 bpp, palette) et **FB16** (RGB565)
- Résolutions configurables (ex : 320×240)
- Primitives graphiques : rectangle fill et line drawing (Bresenham)
- VBlank / VSync pour la synchronisation

### ✅ Recommandation pour Pong

**Le profil vidéo existant est ADAPTÉ pour Pong.** Simplifications recommandées :

#### Profil Pong minimal :

**Ports à utiliser :**
- `0x30` : VID_MODE = 1 (FB8)
- `0x31-0x34` : VID_RES_W_LO/HI, VID_RES_H_LO/HI = 160×120
- `0x35-0x36` : VID_STRIDE_LO/HI = 160 (largeur = stride)
- `0x37-0x38` : VID_FB_ADDR_LO/HI = pointeur dans RAM (ex : 0x8000)
- `0x3B-0x3C` : VID_CLEAR_COLOR_LO/HI = 0 (noir)
- `0x3D` : VID_CLEAR (opcode)
- `0x3A` : VID_FLIP (opcode)
- **0x3E** : RECT_EXEC (optionnel, pour dessiner les palettes)
- **0x3F** : LINE_EXEC (optionnel, pour la balle)

**Modèle d'accès (monochrome simplifié) :**

```
Framebuffer RAM : 160 × 120 = 19200 octets (en FB8)
Format : 1 octet = 1 pixel
  - 0x00 = noir (off)
  - 0xFF = blanc (on)

Adresse pixel(x, y) = FB_BASE + y * 160 + x
```

#### Initialisation standard :

```lisp
; Init vidéo 160×120
(push 1)      (out 0x30)     ; VID_MODE = 1 (FB8)
(push 0xA0)   (out 0x31)     ; VID_RES_W_LO = 160
(push 0x00)   (out 0x32)     ; VID_RES_W_HI
(push 0x78)   (out 0x33)     ; VID_RES_H_LO = 120
(push 0x00)   (out 0x34)     ; VID_RES_H_HI
(push 0xA0)   (out 0x35)     ; VID_STRIDE_LO = 160
(push 0x00)   (out 0x36)     ; VID_STRIDE_HI
(push 0x00)   (out 0x37)     ; VID_FB_ADDR_LO = 0x8000
(push 0x80)   (out 0x38)     ; VID_FB_ADDR_HI
(push 0x00)   (out 0x3B)     ; Clear color LO = 0
(push 0x00)   (out 0x3C)     ; Clear color HI = 0
(push 1)      (out 0x3D)     ; Clear screen
(push 1)      (out 0x3A)     ; Flip
```

#### Notes d'implémentation :

- **Pas de palette complexe** : en FB8, utiliser les 256 niveaux de gris (n → RGB(n,n,n))
- **Collision par pixel** : possible de lire le framebuffer RAM pour vérifier les collisions (deux rectangles se chevauchent-ils ?)
- **Dessin sans primitives** : Si 0x3E et 0x3F ne sont pas supportées, Pong peut les émuler avec des boucles SPL imbriquées

---

## T1.2 — Spécifier les ports clavier pour Pong

### 📋 Analyse de la spécification existante

La spécification SPL (section 14, "Clavier — Port-Mapped I/O") définit :
- `0x20` : KBD_DATA (R) — lit un octet (scancode)
- `0x21` : KBD_STATUS (R) — bit0 = data ready
- `0x22` : KBD_MODS (R) — bits de modifieurs
- `0x23` : KBD_CLEAR (W) — vide la file

**Modèle** : file non-bloquante avec scancodes. Recommandation : ASCII pour alphanum + codes spéciaux.

### ❓ Problème pour Pong

- Pong a besoin de **4 touches directionnelles (UP, DOWN, LEFT, RIGHT)** en **polling d'état** (pas de file d'événements)
- Le modèle "file de scancodes" n'est pas idéal pour le gameplay temps réel
- Besoin : lire l'état **courant** de 4 touches (appuyée = 1, relâchée = 0)

### ✅ Recommandation pour Pong

**Ajouter un profil optionnel simplifiée : Keyboard State Polling (0x24-0x27)**

#### Ports proposés :

| Port | Nom           | R/W | Description                    |
|------|---------------|-----|--------------------------------|
| 0x24 | KBD_KEY_UP    | R   | 1 = touche UP enfoncée, 0 sinon |
| 0x25 | KBD_KEY_DOWN  | R   | 1 = touche DOWN enfoncée       |
| 0x26 | KBD_KEY_LEFT  | R   | 1 = touche LEFT enfoncée       |
| 0x27 | KBD_KEY_RIGHT | R   | 1 = touche RIGHT enfoncée      |

#### Utilisation dans Pong :

```lisp
; Lire l'état des touches (polling)
(in 0x24) (push 1) (and) ; résultat = 1 si UP
(jump-if-zero skip_up)
  ; ... déplacer palette vers le haut ...
(label skip_up)

(in 0x25) (push 1) (and) ; résultat = 1 si DOWN
(jump-if-zero skip_down)
  ; ... déplacer palette vers le bas ...
(label skip_down)
```

#### Notes d'implémentation :

- **Polling uniquement** : chaque lecture retourne l'état **courant**
- **Non-destructif** : contrairement à KBD_DATA qui consomme, ce modèle ne consomme rien
- **Mappage clavier VM** :
  - UP = flèche haut (↑) ou W
  - DOWN = flèche bas (↓) ou S
  - LEFT = flèche gauche (←) ou A
  - RIGHT = flèche droite (→) ou D

---

## T1.3 — Clarifier le timer pour synchronisation 60 FPS

### 📋 Analyse de la spécification existante

La spécification SPL (section 11.3 et 16.2) définit un compteur 32-bit en millisecondes :
- `0x11` : TIME_MS_B0 (bits 0-7)
- `0x12` : TIME_MS_B1 (bits 8-15)
- `0x13` : TIME_MS_B2 (bits 16-23)
- `0x14` : TIME_MS_B3 (bits 24-31, **latch**)

**Modèle** : compteur monotone ; lecture de B3 (0x14) verrouille la valeur complète.

### ✅ Recommandation pour Pong (60 FPS)

**Calcul :** 60 FPS = 1 frame / 16.67 ms ≈ 16-17 ms par frame

#### Pattern de synchronisation recommandé :

```lisp
; Boucle principale du jeu
(label main-loop)

; Lire timestamp au début de la frame
(in 0x14)            ; latch B3 (32-bit)
(push 0)             ; dummy, on le poppe après
(drop)
(in 0x13)            ; lit B2
; ... stocker dans RAM si nécessaire ...

; Faire logique du jeu
; (déplacer palettes, balle, détection collisions...)

; Lire timestamp après logique
(in 0x14)            ; latch B3
(push 0)
(drop)
(in 0x13)            ; lit B2

; Attendre si frame trop rapide
; Si (temps_fin - temps_début) < 17, attendre

(jump main-loop)
```

#### Simplifié : Pattern sans attente (recommandé pour MVP) :

```lisp
; Frame-skipping simple : exécute au maximum 60x/sec
(label main-loop)

; Logique du jeu (déplacer, collider, dessiner)
; ...

; Attendre ~16.67ms avec une boucle de délai
; (voir section "Délai proposé" ci-dessous)

(jump main-loop)
```

#### Délai proposé : ~16.67 ms

```lisp
; Macro de délai ~16.67ms (approximatif)
; Supposant une exécution de base du SPL
(macro delay-16ms
  (push 0)         ; compteur
  (label delay-loop)
  (push 1) (add)
  (push 200)       ; itérations (ajuster selon VM speed)
  (over)
  (swap)
  (lt)
  (jump-if-not-zero delay-loop)
  (drop) (drop))   ; nettoyer stack
```

#### Timing précis (si VM le supporte) :

```lisp
; Alternative : attendre timestamp (6.67ms) exactement
(label wait-frame)
(in 0x14)          ; latch
(drop)
(in 0x13)          ; B2 courant
; ... comparer avec référence + 17 ms ...
; si < 17ms écoulés, boucler
(jump-if-not-zero wait-frame)
```

### ⚠️ Notes importantes :

1. **Granularité** : le timer a une résolution en ms, donc 16.67 ms ne peut être que approximé (16 ou 17)
2. **Order de lecture** : TOUJOURS lire `0x14` en premier (latch), puis `0x13`, `0x12`, `0x11` pour une valeur atomique
3. **Overflow** : 32-bit ms = ~49 jours avant overflow. Pas d'enjeu pour Pong
4. **V-Sync** : Pong peut aussi attendre VBlank (section 16.1) via `VID_STATUS` (0x39, bit0 = 1 en vblank) si implémenté

---

## 📋 Résumé — Actions pour la Phase 2

**Phase 2** va mettre à jour **SPL-spec-fr.md** pour ajouter/clarifier :

1. **Section 12 (Vidéo)** :
   - ✅ Déjà complète ; noter le profil Pong 160×120 comme cas d'usage

2. **Section 14 (Clavier)** :
   - ❌ AJOUTER : ports 0x24-0x27 (KBD_KEY_UP/DOWN/LEFT/RIGHT)
   - Documenter le modèle polling d'état vs. file d'événements

3. **Section 16 (Timing)** :
   - ✅ CLARIFIER : pattern de synchronisation 60 FPS avec timer 32-bit
   - Ajouter exemple SPL de boucle de jeu
   - Documenter order de lecture (B3 → B2 → B1 → B0)

4. **Section 18 (Profils)** :
   - ✅ AJOUTER : profil SPL-Pong-Minimal (160×120 FB8, 4 touches, 60 FPS)

---

## 🎯 Conclusion de Phase 1

**T1.1 ✅ Vidéo** : Spec existante est complète ; cas Pong (160×120 monochrome) est un cas particulier supporté
**T1.2 ⚠️ Clavier** : Spec existante (file) n'est pas idéale ; **recommandation : ajouter ports 0x24-0x27** pour polling d'état
**T1.3 ✅ Timer** : Spec existante est adéquate ; **recommandation : documenter pattern 60 FPS** plus clairement

**Prochaine étape :** Phase 2 (T2.1, T2.2) — Mettre à jour SPL-spec-fr.md avec les recommandations ci-dessus.
