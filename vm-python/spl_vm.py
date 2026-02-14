#!/usr/bin/env python3
"""SPL Virtual Machine — Executes .rom bytecode files.

Usage: python spl_vm.py <program.rom>

Architecture:
  - Harvard: separate code space (ROM) and data memory (64 KiB RAM)
  - Work stack: 256 entries (8-bit values)
  - Return stack: 64 entries (16-bit addresses)
  - Port-mapped I/O: console, RNG, timer, video (FB8/FB16), audio (PSG4), SYSCTL_CAPS

Audio requires: pip install sounddevice numpy
"""

import sys
import os
import time
import random
import math
import threading

try:
    import sounddevice as sd
    import numpy as np
    _HAS_AUDIO = True
except ImportError:
    _HAS_AUDIO = False

# ---------------------------------------------------------------------------
# Opcodes
# ---------------------------------------------------------------------------

OP_HALT             = 0x00
OP_PUSH             = 0x01
OP_DROP             = 0x02
OP_DUP              = 0x03
OP_SWAP             = 0x04
OP_OVER             = 0x05
OP_ADD              = 0x10
OP_SUB              = 0x11
OP_MUL              = 0x12
OP_DIV              = 0x13
OP_MOD              = 0x14
OP_AND              = 0x15
OP_OR               = 0x16
OP_XOR              = 0x17
OP_NOT              = 0x18
OP_LT               = 0x19
OP_GT               = 0x1A
OP_LOAD             = 0x20
OP_STORE            = 0x21
OP_LOAD_INDIRECT    = 0x22
OP_STORE_INDIRECT   = 0x23
OP_JUMP             = 0x30
OP_JUMP_IF_ZERO     = 0x31
OP_JUMP_IF_NOT_ZERO = 0x32
OP_CALL             = 0x33
OP_RETURN           = 0x34
OP_IN               = 0x40
OP_OUT              = 0x41

# SYSCTL_CAPS: console status + flush + RNG + timer + video + audio + mouse
CAPS_VALUE = 0xEF


# ---------------------------------------------------------------------------
# Audio subsystem (PSG 4 channels via sounddevice)
# ---------------------------------------------------------------------------

class AudioChannel:
    """State for one PSG channel."""
    __slots__ = ('freq', 'volume', 'waveform', 'gate', 'phase')

    def __init__(self):
        self.freq = 0       # 16-bit Hz
        self.volume = 0     # 0..15
        self.waveform = 0   # 0=sine,1=square,2=tri,3=saw,4=noise
        self.gate = 0       # 0=off, 1=on
        self.phase = 0.0    # running phase [0, 1)


class AudioSubsystem:
    """PSG 4-channel synthesizer. Uses sounddevice for real-time output."""

    SAMPLE_RATE = 44100
    BLOCK_SIZE = 512

    def __init__(self):
        self.channels = [AudioChannel() for _ in range(4)]
        self.selected = 0
        self.master_vol = 15
        self._stream = None
        self._lock = threading.Lock()
        self._started = False
        self._noise_state = [0xACE1] * 4  # LFSR per channel

    def _ensure_started(self):
        """Lazily start the audio stream on first gate-on."""
        if self._started or not _HAS_AUDIO:
            return
        self._started = True
        try:
            self._stream = sd.OutputStream(
                samplerate=self.SAMPLE_RATE,
                channels=1,
                dtype='float32',
                blocksize=self.BLOCK_SIZE,
                callback=self._audio_callback,
            )
            self._stream.start()
        except Exception as e:
            print(f"[audio] Could not open audio device: {e}", file=sys.stderr)
            self._stream = None

    def _audio_callback(self, outdata, frames, time_info, status):
        """Called by sounddevice to fill audio buffer."""
        buf = np.zeros(frames, dtype=np.float32)
        sr = self.SAMPLE_RATE

        with self._lock:
            master = self.master_vol / 15.0
            for i, ch in enumerate(self.channels):
                if not ch.gate or ch.volume == 0 or ch.freq == 0:
                    continue
                vol = (ch.volume / 15.0) * master * 0.25  # 0.25 = mix headroom
                freq = ch.freq
                phase = ch.phase
                phase_inc = freq / sr
                wf = ch.waveform

                if wf == 4:  # noise
                    lfsr = self._noise_state[i]
                    for j in range(frames):
                        # Generate noise at the given frequency rate
                        phase += phase_inc
                        if phase >= 1.0:
                            phase -= 1.0
                            # LFSR step (16-bit, taps at bits 0,2,3,5)
                            bit = ((lfsr >> 0) ^ (lfsr >> 2) ^
                                   (lfsr >> 3) ^ (lfsr >> 5)) & 1
                            lfsr = ((lfsr >> 1) | (bit << 15)) & 0xFFFF
                        buf[j] += vol * ((lfsr & 1) * 2.0 - 1.0)
                    self._noise_state[i] = lfsr
                    ch.phase = phase
                else:
                    # Vectorised generation for tonal waveforms
                    t = np.arange(frames, dtype=np.float64) * phase_inc + phase
                    t = t % 1.0
                    if wf == 0:    # sine
                        wave = np.sin(2.0 * np.pi * t).astype(np.float32)
                    elif wf == 1:  # square
                        wave = np.where(t < 0.5,
                                        np.float32(1.0),
                                        np.float32(-1.0))
                    elif wf == 2:  # triangle
                        wave = (4.0 * np.abs(t - 0.5) - 1.0).astype(np.float32)
                    elif wf == 3:  # sawtooth
                        wave = (2.0 * t - 1.0).astype(np.float32)
                    else:
                        wave = np.zeros(frames, dtype=np.float32)
                    buf += vol * wave
                    ch.phase = float(t[-1]) + phase_inc if frames > 0 else phase
                    # Keep phase in [0, 1)
                    ch.phase %= 1.0

        # Clip to [-1, 1]
        np.clip(buf, -1.0, 1.0, out=buf)
        outdata[:, 0] = buf

    def set_port(self, port, val):
        with self._lock:
            if port == 0x50:    # AUD_CH_SELECT
                self.selected = val & 0x03
            elif port == 0x57:  # AUD_MASTER_VOL
                self.master_vol = min(val, 15)
            else:
                ch = self.channels[self.selected]
                if port == 0x51:    # AUD_FREQ_LO
                    ch.freq = (ch.freq & 0xFF00) | val
                elif port == 0x52:  # AUD_FREQ_HI
                    ch.freq = (ch.freq & 0x00FF) | (val << 8)
                elif port == 0x53:  # AUD_VOLUME
                    ch.volume = min(val, 15)
                elif port == 0x54:  # AUD_WAVEFORM
                    ch.waveform = min(val, 4)
                elif port == 0x55:  # AUD_GATE
                    ch.gate = 1 if val else 0
                    if ch.gate:
                        ch.phase = 0.0
                        self._ensure_started()

    def get_port(self, port):
        if port == 0x56:  # AUD_STATUS
            return 0x01 if self._started and self._stream else 0x00
        if port == 0x59:  # PCM_STATUS (no FIFO implemented)
            return 0x00
        return 0

    def shutdown(self):
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# Video subsystem (lazy tkinter)
# ---------------------------------------------------------------------------

class VideoSubsystem:
    """Handles framebuffer rendering via tkinter. Created lazily on first flip."""

    def __init__(self):
        self.mode = 0           # 0=off, 1=FB8, 2=FB16
        self.width = 0
        self.height = 0
        self.stride = 0
        self.fb_addr = 0
        self.clear_lo = 0
        self.clear_hi = 0
        # tkinter state (created on first flip)
        self._root = None
        self._canvas = None
        self._photo = None
        self._scale = 1
        self._closed = False
        # Mouse state
        self.mouse_x = 0
        self.mouse_y = 0
        self.mouse_buttons = 0
        self.mouse_wheel = 0
        self.mouse_status = 0

    def set_port(self, port, val):
        if port == 0x30:
            self.mode = val
        elif port == 0x31:
            self.width = (self.width & 0xFF00) | val
        elif port == 0x32:
            self.width = (self.width & 0x00FF) | (val << 8)
        elif port == 0x33:
            self.height = (self.height & 0xFF00) | val
        elif port == 0x34:
            self.height = (self.height & 0x00FF) | (val << 8)
        elif port == 0x35:
            self.stride = (self.stride & 0xFF00) | val
        elif port == 0x36:
            self.stride = (self.stride & 0x00FF) | (val << 8)
        elif port == 0x37:
            self.fb_addr = (self.fb_addr & 0xFF00) | val
        elif port == 0x38:
            self.fb_addr = (self.fb_addr & 0x00FF) | (val << 8)
        elif port == 0x3B:
            self.clear_lo = val
        elif port == 0x3C:
            self.clear_hi = val

    def _read_u16_from_memory(self, memory, addr):
        """Read 16-bit value from memory (little-endian: LO at addr, HI at addr+1)."""
        lo = memory[addr] if addr < len(memory) else 0
        hi = memory[addr + 1] if addr + 1 < len(memory) else 0
        return lo | (hi << 8)

    def rect_exec_with_memory(self, memory):
        """Execute rectangle fill from parameter buffer at 0x0000-0x0009."""
        x = self._read_u16_from_memory(memory, 0x0000)
        y = self._read_u16_from_memory(memory, 0x0002)
        w = self._read_u16_from_memory(memory, 0x0004)
        h = self._read_u16_from_memory(memory, 0x0006)
        color = self._read_u16_from_memory(memory, 0x0008)
        self.rect_fill(memory, x, y, w, h, color)

    def rect_fill(self, memory, x, y, w, h, color):
        """Fill a rectangle at (x, y) with size (w, h) with the given color.

        Handles both FB8 and FB16 modes with automatic clipping.
        """
        if self.mode == 0 or w <= 0 or h <= 0:
            return

        fb = self.fb_addr
        stride = self.stride
        video_w, video_h = self.width, self.height

        # Clip to screen bounds
        x1 = max(0, x)
        y1 = max(0, y)
        x2 = min(video_w, x + w)
        y2 = min(video_h, y + h)

        if x1 >= x2 or y1 >= y2:
            return  # Completely off-screen

        if self.mode == 1:  # FB8
            color_byte = color & 0xFF
            for yy in range(y1, y2):
                base = fb + yy * stride
                for xx in range(x1, x2):
                    addr = base + xx
                    if addr < len(memory):
                        memory[addr] = color_byte

        elif self.mode == 2:  # FB16
            for yy in range(y1, y2):
                base = fb + yy * stride
                for xx in range(x1, x2):
                    addr = base + 2 * xx
                    if addr + 1 < len(memory):
                        memory[addr] = color & 0xFF
                        memory[addr + 1] = (color >> 8) & 0xFF

    def line_exec_with_memory(self, memory):
        """Execute line draw from parameter buffer at 0x0000-0x0009."""
        x0 = self._read_u16_from_memory(memory, 0x0000)
        y0 = self._read_u16_from_memory(memory, 0x0002)
        x1 = self._read_u16_from_memory(memory, 0x0004)
        y1 = self._read_u16_from_memory(memory, 0x0006)
        color = self._read_u16_from_memory(memory, 0x0008)
        self.bresenham_line(memory, x0, y0, x1, y1, color)

    def bresenham_line(self, memory, x0, y0, x1, y1, color):
        """Draw a line from (x0, y0) to (x1, y1) using Bresenham's algorithm.

        Semi-open line: includes start point, excludes end point.
        Automatically clips to screen bounds.
        """
        if self.mode == 0:
            return

        fb = self.fb_addr
        stride = self.stride
        video_w, video_h = self.width, self.height

        # Clip coordinates to screen bounds
        def clip_point(x, y):
            return max(0, min(video_w - 1, x)), max(0, min(video_h - 1, y))

        # Simple clipping: if both endpoints are outside on same side, skip
        if (x0 < 0 and x1 < 0) or (x0 >= video_w and x1 >= video_w):
            if (y0 < 0 and y1 < 0) or (y0 >= video_h and y1 >= video_h):
                return

        # Bresenham's algorithm
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x1 > x0 else -1
        sy = 1 if y1 > y0 else -1
        err = dx - dy

        x, y = x0, y0

        while True:
            # Plot pixel if in bounds
            if 0 <= x < video_w and 0 <= y < video_h:
                if self.mode == 1:  # FB8
                    addr = fb + y * stride + x
                    if addr < len(memory):
                        memory[addr] = color & 0xFF
                elif self.mode == 2:  # FB16
                    addr = fb + y * stride + 2 * x
                    if addr + 1 < len(memory):
                        memory[addr] = color & 0xFF
                        memory[addr + 1] = (color >> 8) & 0xFF

            # Check if we've reached the end point
            if x == x1 and y == y1:
                break

            # Bresenham step
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x += sx
            if e2 < dx:
                err += dx
                y += sy

    def get_port(self, port):
        if port == 0x39:    # VID_STATUS: vblank=1, fb-ready=1
            return 0x03 if self.mode != 0 else 0
        return 0

    def clear(self, memory):
        """Fill the framebuffer region in memory with the clear color."""
        if self.mode == 0 or self.width == 0 or self.height == 0:
            return
        fb = self.fb_addr
        w, h, stride = self.width, self.height, self.stride

        if self.mode == 1:  # FB8
            color = self.clear_lo
            for y in range(h):
                base = fb + y * stride
                for x in range(w):
                    addr = base + x
                    if addr < len(memory):
                        memory[addr] = color
        elif self.mode == 2:  # FB16
            for y in range(h):
                base = fb + y * stride
                for x in range(w):
                    addr = base + 2 * x
                    if addr + 1 < len(memory):
                        memory[addr] = self.clear_lo
                        memory[addr + 1] = self.clear_hi

    def flip(self, memory):
        """Render the framebuffer to a tkinter window."""
        if self._closed or self.mode == 0 or self.width == 0 or self.height == 0:
            return
        import tkinter as tk

        w, h = self.width, self.height
        stride = self.stride
        fb = self.fb_addr
        scale = max(1, min(8, 512 // max(w, h)))
        self._scale = scale

        # Create window on first flip
        if self._root is None:
            self._root = tk.Tk()
            self._root.title("SPL Video")
            self._root.resizable(False, False)
            self._canvas = tk.Canvas(
                self._root, width=w * scale, height=h * scale,
                bg="black", highlightthickness=0,
            )
            self._canvas.pack()
            self._bind_mouse()
            self.mouse_status = 0x01  # mouse present

        # Build the image row by row
        photo = tk.PhotoImage(width=w, height=h)

        if self.mode == 1:  # FB8 grayscale
            for y in range(h):
                row_colors = []
                base = fb + y * stride
                for x in range(w):
                    addr = base + x
                    v = memory[addr] if addr < len(memory) else 0
                    row_colors.append(f"#{v:02x}{v:02x}{v:02x}")
                photo.put("{" + " ".join(row_colors) + "}", to=(0, y))

        elif self.mode == 2:  # FB16 RGB565
            for y in range(h):
                row_colors = []
                base = fb + y * stride
                for x in range(w):
                    addr = base + 2 * x
                    if addr + 1 < len(memory):
                        lo, hi = memory[addr], memory[addr + 1]
                    else:
                        lo, hi = 0, 0
                    rgb565 = (hi << 8) | lo
                    r = ((rgb565 >> 11) & 0x1F) * 255 // 31
                    g = ((rgb565 >> 5) & 0x3F) * 255 // 63
                    b = (rgb565 & 0x1F) * 255 // 31
                    row_colors.append(f"#{r:02x}{g:02x}{b:02x}")
                photo.put("{" + " ".join(row_colors) + "}", to=(0, y))

        # Scale up for small framebuffers
        if scale > 1:
            photo = photo.zoom(scale, scale)

        self._canvas.delete("all")
        self._canvas.create_image(0, 0, anchor=tk.NW, image=photo)
        self._photo = photo  # prevent garbage collection
        try:
            self._root.update()
        except Exception:
            self._closed = True

    # --- Mouse event handlers ---

    def _bind_mouse(self):
        self._canvas.bind("<Motion>", self._on_mouse_motion)
        self._canvas.bind("<Button-1>", lambda e: self._on_mouse_btn(e, True))
        self._canvas.bind("<ButtonRelease-1>", lambda e: self._on_mouse_btn(e, False))
        self._canvas.bind("<Button-2>", lambda e: self._on_mouse_btn(e, True))
        self._canvas.bind("<ButtonRelease-2>", lambda e: self._on_mouse_btn(e, False))
        self._canvas.bind("<Button-3>", lambda e: self._on_mouse_btn(e, True))
        self._canvas.bind("<ButtonRelease-3>", lambda e: self._on_mouse_btn(e, False))
        self._canvas.bind("<MouseWheel>", self._on_mouse_wheel)
        self._root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_mouse_motion(self, event):
        self.mouse_x = max(0, min(self.width - 1, event.x // self._scale))
        self.mouse_y = max(0, min(self.height - 1, event.y // self._scale))
        self.mouse_status |= 0x03  # present + movement

    def _on_mouse_btn(self, event, pressed):
        bit = {1: 0x01, 2: 0x04, 3: 0x02}.get(event.num, 0)
        if pressed:
            self.mouse_buttons |= bit
        else:
            self.mouse_buttons &= ~bit
        self.mouse_status |= 0x01

    def _on_mouse_wheel(self, event):
        delta = event.delta // 120
        self.mouse_wheel = max(-128, min(127, self.mouse_wheel + delta))

    def _on_close(self):
        self._closed = True
        if self._root:
            self._root.destroy()
            self._root = None

    def get_mouse_port(self, port):
        if port == 0x70: return self.mouse_x & 0xFF
        if port == 0x71: return (self.mouse_x >> 8) & 0xFF
        if port == 0x72: return self.mouse_y & 0xFF
        if port == 0x73: return (self.mouse_y >> 8) & 0xFF
        if port == 0x74: return self.mouse_buttons
        if port == 0x75: return self.mouse_wheel & 0xFF
        if port == 0x76: return self.mouse_status
        return 0

    def clear_mouse(self):
        self.mouse_status &= ~0x02  # keep present, clear movement
        self.mouse_wheel = 0

    def keep_open(self):
        """Enter mainloop to keep the window visible after the VM halts."""
        if self._root is not None and not self._closed:
            self._root.mainloop()


# ---------------------------------------------------------------------------
# VM
# ---------------------------------------------------------------------------

class SPLVM:
    MEMORY_SIZE = 65536   # 64 KiB
    MAX_STACK   = 256
    MAX_RSTACK  = 64

    def __init__(self, code):
        self.code = code
        self.code_len = len(code)
        self.memory = bytearray(self.MEMORY_SIZE)
        self.stack = []
        self.rstack = []
        self.pc = 0
        self.running = True

        # Console output buffer
        self.console_buf = bytearray()

        # Timer
        self.start_time_ns = time.monotonic_ns()
        self.time_latch = None

        # Video
        self.video = VideoSubsystem()

        # Audio
        self.audio = AudioSubsystem()

    # --- Stack operations ---

    def push(self, val):
        if len(self.stack) >= self.MAX_STACK:
            self.fault("stack overflow")
        self.stack.append(val & 0xFF)

    def pop(self):
        if not self.stack:
            self.fault("stack underflow")
        return self.stack.pop()

    def rpush(self, val):
        if len(self.rstack) >= self.MAX_RSTACK:
            self.fault("return stack overflow")
        self.rstack.append(val & 0xFFFF)

    def rpop(self):
        if not self.rstack:
            self.fault("return stack underflow")
        return self.rstack.pop()

    # --- Code reading ---

    def read_byte(self):
        if self.pc >= self.code_len:
            self.fault("unexpected end of bytecode (reading byte argument)")
        val = self.code[self.pc]
        self.pc += 1
        return val

    def read_addr(self):
        if self.pc + 1 >= self.code_len:
            self.fault("unexpected end of bytecode (reading 16-bit address)")
        hi = self.code[self.pc]
        lo = self.code[self.pc + 1]
        self.pc += 2
        return (hi << 8) | lo

    # --- Error handling ---

    def fault(self, msg):
        self.flush_console()
        print(f"\nVM FAULT at PC=0x{self.pc:04X}: {msg}", file=sys.stderr)
        self.running = False
        sys.exit(1)

    # --- I/O ---

    def port_in(self, port):
        if port == 0x02:        # CONSOLE_STATUS
            return 1

        elif port == 0x10:      # RNG8
            return random.randint(0, 255)

        elif port == 0x14:      # TIME_MS_B3 — latches
            self.time_latch = self._get_time_ms()
            return (self.time_latch >> 24) & 0xFF
        elif port == 0x13:      # TIME_MS_B2
            t = self.time_latch if self.time_latch is not None else self._get_time_ms()
            return (t >> 16) & 0xFF
        elif port == 0x12:      # TIME_MS_B1
            t = self.time_latch if self.time_latch is not None else self._get_time_ms()
            return (t >> 8) & 0xFF
        elif port == 0x11:      # TIME_MS_B0 — releases latch
            t = self.time_latch if self.time_latch is not None else self._get_time_ms()
            self.time_latch = None
            return t & 0xFF

        elif 0x30 <= port <= 0x3F:  # Video
            return self.video.get_port(port)

        elif port in (0x56, 0x59):  # Audio status
            return self.audio.get_port(port)

        elif 0x70 <= port <= 0x76:  # Mouse
            return self.video.get_mouse_port(port)

        elif port == 0xFF:      # SYSCTL_CAPS
            return CAPS_VALUE

        return 0

    def port_out(self, port, val):
        if port == 0x01:        # CONSOLE_DATA
            self.console_buf.append(val)
            if val == 0x0A:
                self.flush_console()
        elif port == 0x03:      # CONSOLE_FLUSH
            self.flush_console()

        elif port == 0x3A:      # VID_FLIP
            self.video.flip(self.memory)
        elif port == 0x3D:      # VID_CLEAR
            self.video.clear(self.memory)
        elif port == 0x3E:      # RECT_EXEC
            self.video.rect_exec_with_memory(self.memory)
        elif port == 0x3F:      # LINE_EXEC
            self.video.line_exec_with_memory(self.memory)
        elif 0x30 <= port <= 0x3C:  # Video config ports
            self.video.set_port(port, val)
        elif port == 0x77:      # MOUSE_CLEAR
            self.video.clear_mouse()

        elif 0x50 <= port <= 0x58:  # Audio
            self.audio.set_port(port, val)

    def flush_console(self):
        if self.console_buf:
            sys.stdout.buffer.write(bytes(self.console_buf))
            sys.stdout.buffer.flush()
            self.console_buf.clear()

    def _get_time_ms(self):
        elapsed_ns = time.monotonic_ns() - self.start_time_ns
        return (elapsed_ns // 1_000_000) & 0xFFFFFFFF

    # --- Execution ---

    def run(self):
        code = self.code
        code_len = self.code_len

        while self.running:
            if self.pc >= code_len:
                break

            opcode = code[self.pc]
            self.pc += 1

            if opcode == OP_HALT:
                break

            elif opcode == OP_PUSH:
                self.push(self.read_byte())
            elif opcode == OP_DROP:
                self.pop()
            elif opcode == OP_DUP:
                a = self.pop(); self.push(a); self.push(a)
            elif opcode == OP_SWAP:
                b = self.pop(); a = self.pop(); self.push(b); self.push(a)
            elif opcode == OP_OVER:
                b = self.pop(); a = self.pop(); self.push(a); self.push(b); self.push(a)

            elif opcode == OP_ADD:
                b = self.pop(); a = self.pop(); self.push((a + b) & 0xFF)
            elif opcode == OP_SUB:
                b = self.pop(); a = self.pop(); self.push((a - b) & 0xFF)
            elif opcode == OP_MUL:
                b = self.pop(); a = self.pop(); self.push((a * b) & 0xFF)
            elif opcode == OP_DIV:
                b = self.pop(); a = self.pop(); self.push(0 if b == 0 else (a // b) & 0xFF)
            elif opcode == OP_MOD:
                b = self.pop(); a = self.pop(); self.push(0 if b == 0 else (a % b) & 0xFF)

            elif opcode == OP_AND:
                b = self.pop(); a = self.pop(); self.push(a & b)
            elif opcode == OP_OR:
                b = self.pop(); a = self.pop(); self.push(a | b)
            elif opcode == OP_XOR:
                b = self.pop(); a = self.pop(); self.push(a ^ b)
            elif opcode == OP_NOT:
                self.push((~self.pop()) & 0xFF)
            elif opcode == OP_LT:
                b = self.pop(); a = self.pop(); self.push(1 if a < b else 0)
            elif opcode == OP_GT:
                b = self.pop(); a = self.pop(); self.push(1 if a > b else 0)

            elif opcode == OP_LOAD:
                addr = self.read_addr()
                if addr >= self.MEMORY_SIZE:
                    self.fault(f"load: address 0x{addr:04X} out of bounds")
                self.push(self.memory[addr])
            elif opcode == OP_STORE:
                addr = self.read_addr()
                if addr >= self.MEMORY_SIZE:
                    self.fault(f"store: address 0x{addr:04X} out of bounds")
                self.memory[addr] = self.pop()

            elif opcode == OP_LOAD_INDIRECT:
                lo = self.pop(); hi = self.pop()
                addr = (hi << 8) | lo
                if addr >= self.MEMORY_SIZE:
                    self.fault(f"load-indirect: address 0x{addr:04X} out of bounds")
                self.push(self.memory[addr])
            elif opcode == OP_STORE_INDIRECT:
                lo = self.pop(); hi = self.pop()
                addr = (hi << 8) | lo
                val = self.pop()
                if addr >= self.MEMORY_SIZE:
                    self.fault(f"store-indirect: address 0x{addr:04X} out of bounds")
                self.memory[addr] = val

            elif opcode == OP_JUMP:
                self.pc = self.read_addr()
            elif opcode == OP_JUMP_IF_ZERO:
                addr = self.read_addr()
                if self.pop() == 0: self.pc = addr
            elif opcode == OP_JUMP_IF_NOT_ZERO:
                addr = self.read_addr()
                if self.pop() != 0: self.pc = addr
            elif opcode == OP_CALL:
                addr = self.read_addr(); self.rpush(self.pc); self.pc = addr
            elif opcode == OP_RETURN:
                self.pc = self.rpop()

            elif opcode == OP_IN:
                self.push(self.port_in(self.read_byte()))
            elif opcode == OP_OUT:
                port = self.read_byte(); self.port_out(port, self.pop())

            else:
                self.fault(f"unknown opcode 0x{opcode:02X}")

        self.flush_console()
        self.audio.shutdown()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python spl_vm.py <program.rom>", file=sys.stderr)
        sys.exit(1)

    rom_path = sys.argv[1]

    try:
        with open(rom_path, 'rb') as f:
            code = f.read()
    except FileNotFoundError:
        print(f"Error: file not found: {rom_path}", file=sys.stderr)
        sys.exit(1)

    if not code:
        print("Error: empty ROM file", file=sys.stderr)
        sys.exit(1)

    vm = SPLVM(code)
    vm.run()
    vm.video.keep_open()


if __name__ == '__main__':
    main()
