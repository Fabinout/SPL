# TODO: Implémentation d'un Pong en SPL

## Phase 1: Spécification des ports d'entrée/sortie

### [ ] T1.1 - Spécifier le port vidéo
**Prompt:**
> Ajoute à la spécification SPL un port vidéo (ex. 0x20-0x2F) pour accéder à un framebuffer de 160x120 pixels en 1-bit (noir/blanc). Définis le format d'accès : faut-il écrire l'adresse X/Y puis le pixel? Faut-il passer par la mémoire RAM ou des registres? Propose le mécanisme le plus simple pour un LLM.

### [ ] T1.2 - Spécifier les ports clavier
**Prompt:**
> Ajoute à la spécification SPL des ports clavier (ex. 0x30-0x33) pour lire l'état des 4 touches essentielles : UP, DOWN, LEFT, RIGHT. Définis si c'est du polling (lire l'état courant) ou des événements. Documente le format exact des valeurs retournées.

### [ ] T1.3 - Clarifier le timer pour la synchronisation
**Prompt:**
> Le timer 32-bit existe déjà (port 0x11-0x14). Clarifiez dans la spec : comment un jeu Pong peut l'utiliser pour synchroniser 60 FPS? Faut-il ajouter un port V-sync ou une interruption? Proposez la solution la plus minimaliste.

---

## Phase 2: Mise à jour de la spécification

### [ ] T2.1 - Ajouter les nouveaux ports à SPL-spec-fr.md
**Prompt:**
> Mets à jour la section "Port-Mapped I/O" du SPL-spec-fr.md pour inclure :
> - Port vidéo 0x20-0x2F (accès framebuffer 160x120 monochrome)
> - Ports clavier 0x30-0x33 (UP, DOWN, LEFT, RIGHT)
> - Clarification du timer 0x11-0x14 pour la synchronisation
> Chaque port doit inclure : numéro, mode (R/W), description, format exact des valeurs.

### [ ] T2.2 - Documenter des primitives de dessin recommandées
**Prompt:**
> Ajoute une section "Dessin et géométrie" au SPL-spec-fr.md qui documente les patterns courants (sans ajouter d'opcodes) :
> - Comment dessiner un rectangle rempli (boucles imbriquées + write pixel)
> - Comment dessiner un point
> - Comment vérifier une collision rectangle-rectangle (utile pour le Pong)
> Fournis des pseudocodes en SPL ou des patterns pseudocode génériques.

---

## Phase 3: Mise à jour du VM Python

### [ ] T3.1 - Implémenter le port vidéo dans spl_vm.py
**Prompt:**
> Ajoute au VM Python (spl_vm.py) :
> - Un framebuffer 160x120 en mémoire (1 bit = 1 pixel, stocké dans une liste/array)
> - Ports 0x20-0x2F pour écrire/lire les pixels
> - Port 0x20 (adresse X), 0x21 (adresse Y), 0x22 (valeur pixel 0/1)
> - Ajoute une fonction pour afficher le framebuffer en terminal ASCII (# pour pixel allumé, espace sinon)
> Intègre-la dans la boucle principale du VM.

### [ ] T3.2 - Implémenter les ports clavier dans spl_vm.py
**Prompt:**
> Ajoute au VM Python (spl_vm.py) :
> - Ports 0x30-0x33 pour lire l'état de UP, DOWN, LEFT, RIGHT
> - Mode polling : chaque lecture retourne 1 (touche enfoncée) ou 0 (relâchée)
> - Intègre la détection des touches du clavier (utilise input() en mode non-bloquant ou une librairie simple si nécessaire)
> - Documente comment un programme SPL poll les touches.

### [ ] T3.3 - Ajouter la synchronisation V-sync
**Prompt:**
> Améliore le timer du VM Python pour supporter 60 FPS :
> - Chaque itération de la boucle principale doit prendre environ 16.67 ms (1/60e sec)
> - Ajoute un délai si nécessaire
> - Documente comment un programme Pong peut vérifier le temps écoulé et attendre le V-sync avec `(in 0x11)` (lecture du timer)

---

## Phase 4: Assembler (mise à jour optionnelle)

### [ ] T4.1 - Ajouter des pseudo-instructions de dessin (optionnel)
**Prompt:**
> Optionnel : Ajoute des pseudo-instructions au SPL assembler (spl_asm.py) pour simplifier le dessin :
> - `(draw-rect x y width height)` → génère les opcodes pour tracer un rectangle
> - `(draw-pixel x y)` → écrit un pixel
> - `(check-collision rect1 rect2)` → retourne 1 si collision, 0 sinon
> Chaque pseudo-instruction se déploie en vraies instructions SPL. C'est optionnel mais améliore la DX.

---

## Phase 5: Exemple Pong minimal

### [ ] T5.1 - Créer un exemple Pong basique
**Prompt:**
> Écris un programme SPL complet (examples/pong.spl) qui implémente un Pong minimaliste :
> - 2 palettes (haut/bas, contrôlées par UP/DOWN pour l'une, simulation IA pour l'autre)
> - 1 balle au centre qui rebondit
> - Détection collision avec les palettes et les murs
> - Affichage 160x120 monochrome
> - Boucle de jeu qui synchronise à 60 FPS
> Le code doit être lisible et commenté pour servir de documentation.

### [ ] T5.2 - Tester et déboguer le Pong
**Prompt:**
> Exécute le programme Pong dans le VM Python, teste :
> - Le contrôle des palettes (réponse aux touches)
> - Les collisions balle-palette et balle-mur
> - Le framerate (doit être ~60 FPS)
> - Documente les bugs trouvés et les fixes appliquées.

---

## Phase 6: Tests et validation

### [ ] T6.1 - Ajouter des tests pour les nouveaux ports
**Prompt:**
> Ajoute des tests dans tests/test_all.spl ou un nouveau fichier tests/test_pong.spl :
> - Teste l'écriture/lecture du framebuffer
> - Teste le polling clavier
> - Teste la synchronisation timer
> - Assure que chaque port fonctionne isolément avant de tester le Pong complet.

### [ ] T6.2 - Documenter les limitations connues
**Prompt:**
> Crée un fichier PONG-NOTES.md qui liste :
> - Limitations matérielles du SPL pour le Pong (ex. : pas de sprites, affichage monochrome)
> - Cas limites gérés ou non gérés (ex. : balle coincée dans palette)
> - Améliorations futures possibles (ex. : couleur, son, score en EEPROM)

---

## Notes pour le prompting

Chaque prompt est écrit pour être utilisé directement avec un LLM ou Claude Code :
- Ils sont spécifiques (mentionnent les fichiers, numéros de ports, résolutions)
- Ils incluent des critères de succès implicites (ex. : "doit être lisible et commenté")
- Ils suivent une progression logique : spec → impl → tests → doc

**Ordre recommandé d'exécution:** T1.1 → T1.2 → T1.3 → T2.1 → T2.2 → T3.1 → T3.2 → T3.3 → T4.1 → T5.1 → T5.2 → T6.1 → T6.2

---

## Statut

- [x] Phase 1 complétée ✅
- [x] Phase 2 complétée ✅
- [x] Phase 3 complétée ✅
- [ ] Phase 4 complétée (skipped — optional)
- [x] Phase 5.1 complétée ✅ (T5.1: Pong game created)
- [ ] Phase 5.2 complétée (T5.2: Testing)
- [ ] Phase 6 complétée

**Date de création:** 2026-02-14
**Dernier update:** 2026-02-15 (Phase 5.1 completed — Pong example)

**Résultats Phase 1:**
- ✅ T1.1: Vidéo (160×120 monochrome) — Spec existante compatible
- ⚠️ T1.2: Clavier — Recommandation d'ajouter ports 0x24-0x27 (polling d'état)
- ✅ T1.3: Timer — Pattern 60 FPS clarifié
- 📄 Document d'analyse: PHASE-1-ANALYSIS.md

**Résultats Phase 2:**
- ✅ T2.1: SPL-spec-fr.md mis à jour
  - Section 14.3: Clavier polling (0x24-0x27) — KBD_KEY_UP/DOWN/LEFT/RIGHT
  - Section 16.2: Clarification timer 60 FPS avec patterns SPL
  - Section 17: Mise à jour capabilities
  - Section 18.5: Nouveau profil SPL-Pong-Minimal
- ✅ T2.2: Nouveaux contenu dans SPL-spec-fr.md
  - Section 12.7: Patterns de dessin (point, rectangle, collision AABB)
  - Exemples SPL avec boucles imbriquées
  - Exemple de paddle Pong

**Résultats Phase 3:**
- ✅ T3.1: Ports clavier polling implémentés dans spl_vm.py
  - Ports 0x24-0x27 pour UP/DOWN/LEFT/RIGHT
  - Intégration tkinter pour la capture clavier
  - Touches mappées: ↑/W, ↓/S, ←/A, →/D
  - État de clavier maintenu (1 = appuyée, 0 = relâchée)
- ✅ T3.2: (Implicite dans T3.1) Ports clavier totalement fonctionnels
- ✅ T3.3: Synchronisation 60 FPS implémentée
  - Cible: 16.67 ms par frame
  - Sync après VID_FLIP (port 0x3A)
  - Méthode: `_sync_frame_60fps()` avec time.monotonic()
  - Test: tests/test_keyboard_polling.spl assemblé et validé
