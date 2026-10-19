"""
Unit test cho BoardRestartAnimator (Hoạt ảnh sụp đổ và tái lập sàn khi restart).
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core.map_loader import load_map_from_file
from src.gui.board_animator import BoardRestartAnimator


class TestBoardRestartAnimator(unittest.TestCase):
    def setUp(self):
        self.map_data = load_map_from_file("levels/map01.txt")
        self.anim = BoardRestartAnimator()

    def test_initial_state(self):
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_IDLE)
        self.assertFalse(self.anim.is_animating())
        self.assertFalse(self.anim.should_render_block())

    def test_start_and_phases_sequence(self):
        completed = False

        def on_done():
            nonlocal completed
            completed = True

        self.anim.start(self.map_data, on_complete=on_done)
        self.assertTrue(self.anim.is_animating())
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_FALL)

        # 1. Update in FALL phase
        self.anim.update(0.5)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_FALL)
        self.assertFalse(self.anim.should_render_block())

        # Advance to WAIT phase
        self.anim.update(1.0)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_WAIT)
        self.assertFalse(self.anim.should_render_block())
        self.assertTrue(len(self.anim.hidden_tiles) > 0)

        # Advance to RISE phase
        self.anim.update(0.7)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_RISE)
        self.assertFalse(self.anim.should_render_block())

        # Advance to FLASH phase
        self.anim.update(1.4)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_FLASH)
        self.assertFalse(self.anim.should_render_block())

        # Advance to SPAWN phase
        self.anim.update(0.26)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_SPAWN)
        self.assertTrue(self.anim.should_render_block())
        self.assertGreater(self.anim.get_spawn_z_offset(), 0.0)

        # Complete SPAWN phase
        self.anim.update(0.36)
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_IDLE)
        self.assertFalse(self.anim.is_animating())
        self.assertTrue(completed)

    def test_skip_to_end(self):
        completed = False

        def on_done():
            nonlocal completed
            completed = True

        self.anim.start(self.map_data, on_complete=on_done)
        self.anim.update(0.2)
        self.assertTrue(self.anim.is_animating())

        # Skip immediately
        self.anim.skip_to_end()
        self.assertFalse(self.anim.is_animating())
        self.assertEqual(self.anim.phase, BoardRestartAnimator.PHASE_IDLE)
        self.assertTrue(completed)


if __name__ == "__main__":
    unittest.main()
