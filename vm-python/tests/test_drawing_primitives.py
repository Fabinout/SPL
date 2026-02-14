#!/usr/bin/env python3
"""Unit tests for drawing primitives (rectangle fill and line drawing).

Tests the GraphicsSubsystem directly without needing the full VM.
"""

import sys
import os
import unittest

# Add parent directory to path
ROOT = os.path.join(os.path.dirname(__file__), "..", "..")
sys.path.insert(0, os.path.join(ROOT, "vm-python"))

from spl_vm import VideoSubsystem


class TestRectangleFill(unittest.TestCase):
    """Test rectangle filling primitive."""

    def setUp(self):
        """Create a video subsystem and initialize FB8 mode."""
        self.video = VideoSubsystem()
        self.memory = bytearray(65536)

        # Setup: FB8, 320x240, framebuffer @ 0x8000
        self.video.mode = 1  # FB8
        self.video.width = 320
        self.video.height = 240
        self.video.stride = 320
        self.video.fb_addr = 0x8000

    def test_simple_rectangle(self):
        """Test drawing a simple white rectangle on black background."""
        # Fill rectangle at (10, 10), 5x5, color 255
        self.video.rect_fill(self.memory, 10, 10, 5, 5, 255)

        # Check that pixels are filled
        base = self.video.fb_addr
        for y in range(10, 15):
            for x in range(10, 15):
                addr = base + y * self.video.stride + x
                self.assertEqual(self.memory[addr], 255,
                               f"Pixel at ({x}, {y}) should be 255")

        # Check that adjacent pixels are NOT filled
        addr = base + 10 * self.video.stride + 9  # Left of rectangle
        self.assertEqual(self.memory[addr], 0)
        addr = base + 9 * self.video.stride + 10  # Above rectangle
        self.assertEqual(self.memory[addr], 0)

    def test_rectangle_clipping(self):
        """Test that rectangles are clipped at screen boundaries."""
        # Use a smaller viewport for this test
        self.video.width = 100
        self.video.height = 100
        self.video.stride = 100
        self.video.fb_addr = 0x0000

        # Rectangle that extends beyond screen (100x100)
        self.video.rect_fill(self.memory, 80, 80, 30, 30, 100)

        base = self.video.fb_addr

        # Should draw at (80-99, 80-99)
        for y in range(80, 100):
            for x in range(80, 100):
                addr = base + y * self.video.stride + x
                self.assertEqual(self.memory[addr], 100,
                               f"Pixel at ({x}, {y}) should be clipped and drawn")

        # Should NOT draw at x >= 100
        addr = base + 80 * self.video.stride + 100
        if addr < len(self.memory):
            self.assertEqual(self.memory[addr], 0)

    def test_offscreen_rectangle(self):
        """Test that completely off-screen rectangles are ignored."""
        # Rectangle completely above screen
        self.video.rect_fill(self.memory, 10, -100, 50, 50, 200)

        # Check that nothing was drawn
        base = self.video.fb_addr
        for i in range(base, min(base + 1000, len(self.memory))):
            self.assertEqual(self.memory[i], 0, f"Memory at {i:04x} should not be modified")

    def test_fb16_rectangle(self):
        """Test rectangle drawing in FB16 mode."""
        self.video.mode = 2  # FB16
        self.video.stride = 640  # 320 pixels * 2 bytes

        # Draw red rectangle (RGB565: 0xF800 = red)
        self.video.rect_fill(self.memory, 0, 0, 2, 2, 0xF800)

        base = self.video.fb_addr

        # Check 2x2 pixels
        for y in range(2):
            for x in range(2):
                addr = base + y * self.video.stride + 2 * x
                lo = self.memory[addr]
                hi = self.memory[addr + 1]
                color = lo | (hi << 8)
                self.assertEqual(color, 0xF800, f"Pixel at ({x}, {y}) should be red")


class TestLineBressenham(unittest.TestCase):
    """Test Bresenham line drawing."""

    def setUp(self):
        """Create a video subsystem and initialize FB8 mode."""
        self.video = VideoSubsystem()
        self.memory = bytearray(65536)

        # Setup: FB8, 320x240, framebuffer @ 0x8000
        self.video.mode = 1  # FB8
        self.video.width = 320
        self.video.height = 240
        self.video.stride = 320
        self.video.fb_addr = 0x8000

    def test_horizontal_line(self):
        """Test drawing a horizontal line."""
        self.video.bresenham_line(self.memory, 10, 10, 20, 10, 255)

        base = self.video.fb_addr
        for x in range(10, 20):
            addr = base + 10 * self.video.stride + x
            self.assertEqual(self.memory[addr], 255,
                           f"Pixel at ({x}, 10) should be 255")

    def test_vertical_line(self):
        """Test drawing a vertical line."""
        self.video.bresenham_line(self.memory, 10, 10, 10, 20, 200)

        base = self.video.fb_addr
        for y in range(10, 20):
            addr = base + y * self.video.stride + 10
            self.assertEqual(self.memory[addr], 200,
                           f"Pixel at (10, {y}) should be 200")

    def test_diagonal_line(self):
        """Test drawing a diagonal line (45 degrees)."""
        self.video.bresenham_line(self.memory, 0, 0, 5, 5, 100)

        base = self.video.fb_addr
        # Diagonal line should hit approximately these pixels
        expected = [(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)]
        for x, y in expected:
            addr = base + y * self.video.stride + x
            self.assertEqual(self.memory[addr], 100,
                           f"Pixel at ({x}, {y}) should be on diagonal")

    def test_line_clipping(self):
        """Test that lines are clipped at screen boundaries."""
        # Line from outside to inside screen
        self.video.bresenham_line(self.memory, -10, 10, 10, 10, 150)

        base = self.video.fb_addr
        # Should have pixels from x=0 onwards
        has_pixels = False
        for x in range(320):
            addr = base + 10 * self.video.stride + x
            if self.memory[addr] == 150:
                has_pixels = True
                break
        self.assertTrue(has_pixels, "Clipped line should have at least one pixel")

    def test_fb16_line(self):
        """Test line drawing in FB16 mode."""
        self.video.mode = 2  # FB16
        self.video.stride = 640

        # Draw blue line (RGB565: 0x001F = blue)
        self.video.bresenham_line(self.memory, 0, 0, 10, 0, 0x001F)

        base = self.video.fb_addr
        for x in range(10):
            addr = base + 0 * self.video.stride + 2 * x
            lo = self.memory[addr]
            hi = self.memory[addr + 1]
            color = lo | (hi << 8)
            self.assertEqual(color, 0x001F, f"Pixel at ({x}, 0) should be blue")


class TestIntegration(unittest.TestCase):
    """Integration tests using memory buffer interface."""

    def test_rect_from_buffer_fb8(self):
        """Test rectangle execution reading from memory buffer."""
        video = VideoSubsystem()
        memory = bytearray(65536)

        # Setup FB8
        video.mode = 1
        video.width = 320
        video.height = 240
        video.stride = 320
        video.fb_addr = 0x8000

        # Write rectangle parameters to buffer
        memory[0x0000] = 50   # X_LO
        memory[0x0001] = 0    # X_HI
        memory[0x0002] = 50   # Y_LO
        memory[0x0003] = 0    # Y_HI
        memory[0x0004] = 30   # W_LO
        memory[0x0005] = 0    # W_HI
        memory[0x0006] = 30   # H_LO
        memory[0x0007] = 0    # H_HI
        memory[0x0008] = 200  # Color_LO
        memory[0x0009] = 0    # Color_HI

        # Execute rectangle
        video.rect_exec_with_memory(memory)

        # Verify
        base = video.fb_addr
        addr = base + 50 * video.stride + 50
        self.assertEqual(memory[addr], 200)

    def test_line_from_buffer_fb8(self):
        """Test line execution reading from memory buffer."""
        video = VideoSubsystem()
        memory = bytearray(65536)

        # Setup FB8
        video.mode = 1
        video.width = 320
        video.height = 240
        video.stride = 320
        video.fb_addr = 0x8000

        # Write line parameters to buffer
        memory[0x0000] = 10   # X0_LO
        memory[0x0001] = 0    # X0_HI
        memory[0x0002] = 10   # Y0_LO
        memory[0x0003] = 0    # Y0_HI
        memory[0x0004] = 20   # X1_LO
        memory[0x0005] = 0    # X1_HI
        memory[0x0006] = 10   # Y1_LO
        memory[0x0007] = 0    # Y1_HI
        memory[0x0008] = 180  # Color_LO
        memory[0x0009] = 0    # Color_HI

        # Execute line
        video.line_exec_with_memory(memory)

        # Verify at least one pixel
        base = video.fb_addr
        found = False
        for x in range(10, 20):
            addr = base + 10 * video.stride + x
            if memory[addr] == 180:
                found = True
                break
        self.assertTrue(found, "Line should have drawn at least one pixel")


if __name__ == "__main__":
    unittest.main()
