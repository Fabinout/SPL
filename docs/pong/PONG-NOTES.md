# PONG Game Implementation — Notes and Documentation

**Status:** Phase 5.1 Complete
**Date:** 2026-02-15
**Location:** `examples/pong.spl` (175 instructions, 395 bytes)

---

## Overview

A minimal but complete Pong game implemented in SPL demonstrating:
- Keyboard polling (UP/DOWN keys)
- Framebuffer rendering (160×120 monochrome)
- Rectangle drawing with hardware primitives
- Game logic (ball physics, collisions, paddle control)
- 60 FPS synchronization

## Game Rules

**Controls:**
- **UP** or **W** — Move player paddle up
- **DOWN** or **S** — Move player paddle down

**Game Elements:**
- **Player paddle** (bottom, white): 4×24 pixels, controlled by keyboard
- **AI paddle** (top, white): 4×24 pixels, stationary (no AI logic yet)
- **Ball** (white): 4×4 pixels, bounces around the screen

**Physics:**
- Ball moves at ±1 pixel per frame in X and Y axes
- Ball bounces off left/right walls (reverses X velocity)
- Ball bounces off top/bottom walls (reverses Y velocity)
- Collision with paddles reverses Y velocity (bounces ball up/down)

## Memory Layout

```
0x00: player.x    (paddle X position, 8-bit)
0x01: player.y    (paddle Y position, 8-bit)
0x02: ai.x        (AI paddle X position, 8-bit)
0x03: ai.y        (AI paddle Y position, 8-bit)
0x04: ball.x      (ball X position, 8-bit)
0x05: ball.y      (ball Y position, 8-bit)
0x06: ball.vx     (ball X velocity, signed 8-bit)
0x07: ball.vy     (ball Y velocity, signed 8-bit)

0x0000-0x0009:    Rectangle fill parameter buffer (for port 0x3E)
                  [x_lo, x_hi, y_lo, y_hi, w_lo, w_hi, h_lo, h_hi, color_lo, color_hi]

0x8000-0x8FFF:    Framebuffer (160×120 = 19,200 bytes, FB8 monochrome)
```

## Hardware Configuration

**Video:**
- Mode: FB8 (1 byte per pixel, 0x00=black, 0xFF=white)
- Resolution: 160×120 pixels
- Framebuffer base: 0x8000

**Keyboard:**
- Port 0x24 (UP): 1 if pressed, 0 if released
- Port 0x25 (DOWN): 1 if pressed, 0 if released

**Timer:**
- Port 0x11-0x14: 32-bit millisecond counter
- Automatic 60 FPS sync on VID_FLIP (port 0x3A)

## Game Loop

```
┌─────────────────────────────────────────┐
│ 1. Clear screen (black fill)            │
├─────────────────────────────────────────┤
│ 2. Read keyboard                        │
│    - UP key → Move paddle up (y -= 2)   │
│    - DOWN key → Move paddle down        │
├─────────────────────────────────────────┤
│ 3. Update ball position                 │
│    - ball.x += ball.vx                  │
│    - ball.y += ball.vy                  │
├─────────────────────────────────────────┤
│ 4. Collision detection                  │
│    - Walls: Reverse X/Y velocity        │
│    - Paddles: Reverse Y velocity        │
├─────────────────────────────────────────┤
│ 5. Render                               │
│    - Draw player paddle (rect 4×24)     │
│    - Draw AI paddle (rect 4×24)         │
│    - Draw ball (rect 4×4)               │
├─────────────────────────────────────────┤
│ 6. Flip display + 60 FPS sync           │
│    (port 0x3A triggers _sync_frame_60fps)
└─────────────────────────────────────────┘
        ↓
    Repeat ~60 times per second
```

## Instruction Count

- **175 total instructions**
- **395 bytes bytecode**

Breakdown:
- Video initialization: ~30 bytes
- Game state initialization: ~20 bytes
- Main loop (per frame): ~345 bytes
  - Input polling: ~20 bytes
  - Ball physics: ~20 bytes
  - Wall collisions: ~80 bytes
  - Rendering (3 rects × ~70 bytes): ~210 bytes

## Known Limitations

1. **No AI paddle logic**
   - The AI paddle is stationary at y=4
   - Could be implemented to track ball position

2. **Simple physics**
   - Ball velocity is constant (±1 px/frame)
   - No acceleration or spin
   - Collisions are instantaneous (no collision response delay)

3. **No score/UI**
   - No text rendering (monochrome only)
   - No score tracking
   - No game-over detection

4. **Limited collision detection**
   - Only axis-aligned bounding boxes
   - Ball-paddle collision only reverses Y velocity
   - No edge case handling (ball stuck in paddle)

5. **Monochrome only**
   - No color support (FB8 = grayscale only)
   - Black background, white foreground

6. **No sound**
   - Audio ports exist but game doesn't use them
   - Could add beep on paddle/wall collision

## Testing Notes

**To run:**
```bash
python3 vm-python/spl_asm.py examples/pong.spl examples/pong.rom
python3 vm-python/spl_vm.py examples/pong.rom
```

**Expected behavior:**
- Window opens with 160×120 display (upscaled for visibility)
- Two white rectangles (paddles) at top and bottom
- One white square (ball) bounces around
- Bottom paddle responds to UP/DOWN keys or W/S
- Ball bounces off walls and paddles
- No lag; 60 FPS synchronization prevents runaway speed

**Potential issues:**
- On very slow machines, frame rate may drop below 60 FPS
- Keyboard input may have latency on some systems
- tkinter window scaling may blur pixel-art on some displays

## Future Improvements

1. **AI Paddle**
   ```lisp
   ; Simple AI: track ball Y, move towards it
   (load 0x05)    ; ball.y
   (load 0x03)    ; ai.y
   (sub)          ; delta
   (push 0) (lt)  ; delta < 0? (ball above AI)
   (jump-if-zero ai-down)
     ; Move AI up
     (load 0x03) (push 1) (sub) (store 0x03)
     (jump ai-done)
   (label ai-down)
     ; Move AI down
     (load 0x03) (push 1) (add) (store 0x03)
   (label ai-done)
   ```

2. **Score tracking**
   - Count missed balls (left/right edge)
   - Store in memory or print to console

3. **Variable ball speed**
   - Increase speed based on paddle hits
   - Add randomness to bounce angle

4. **Color support**
   - Use FB16 mode for RGB565
   - Draw paddles in different colors

5. **Sound effects**
   - Use audio ports (0x50-0x59) for PSG synthesis
   - Beep on collision events

## Integration with SPL Specification

This Pong game demonstrates all features from **SPL-Pong-Minimal profile** (Section 18.5):

| Feature | Port Range | Status |
|---------|-----------|--------|
| Console I/O | 0x01-0x03 | ✓ (not used in game) |
| Keyboard polling | 0x24-0x27 | ✓ (UP/DOWN used) |
| Video framebuffer | 0x30-0x3A | ✓ (FB8 160×120) |
| Rectangle primitives | 0x3E | ✓ (RECT_EXEC used) |
| Timer (60 FPS) | 0x11-0x14 | ✓ (auto-sync via 0x3A) |

---

## Code Quality

**Readability:**
- Well-commented sections
- Clear label names (game-loop, draw-game, check-y, etc.)
- Memory layout documented

**Performance:**
- Optimized for 60 FPS target (no frame drops expected)
- Minimal memory usage (~20 bytes state, ~400 bytes code)
- No unbounded loops or recursion

**Compliance:**
- Uses only documented SPL opcodes
- Respects memory boundaries (ball/paddle bounds checking)
- Follows AABB collision detection pattern from spec

---

## Related Files

- `examples/pong.spl` — Source code (175 instructions)
- `examples/pong.rom` — Compiled bytecode (395 bytes)
- `SPL-spec-fr.md` — Specification (Section 18.5: SPL-Pong-Minimal)
- `PHASE-3-IMPLEMENTATION.md` — VM implementation details
- `PONG-IMPLEMENTATION.md` — Master TODO and progress tracker
