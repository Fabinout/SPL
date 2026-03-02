# Pong Game

Classic Pong game implementation in SPL, demonstrating video output, keyboard input, and real-time game logic.

## Files

- **pong.spl** — Full Pong game implementation
- **pong-simple.spl** — Simplified version for learning

## Status

The Pong game demonstrates SPL's capabilities for graphics and interactive applications but is still in development.

## Features

- 2D graphics rendering via framebuffer
- Keyboard-controlled paddles
- Ball physics and collision detection
- Score tracking
- Real-time gameplay at 60 FPS

## How to Run

```bash
python3 vm-python/spl_asm.py projects/pong/pong.spl
python3 vm-python/spl_vm.py projects/pong/pong.rom
```

## Controls

- **Paddle 1:** W/Up and S/Down
- **Paddle 2:** Arrow Up/Down

## Future Work

- Improved AI for single-player mode
- Ball speed progression
- Sound effects (audio port)
- Multiple game modes
