"""
Test suite cho module BlockAnimator (src/gui/animator.py).
Kiểm tra tính toán hình học 3D, physics, lifecycle của animation và các hàm callback.
"""

import unittest
import math
from src.core.block import BlockState, Orientation, Direction
from src.gui.animator import BlockAnimator, Particle


class TestBlockAnimator(unittest.TestCase):

    def setUp(self):
        self.animator = BlockAnimator()

    def test_initial_state(self):
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(self.animator.state, BlockAnimator.STATE_IDLE)
        self.assertEqual(self.animator.progress, 0.0)

    def test_roll_lifecycle(self):
        completed = []
        def on_done():
            completed.append(True)

        block = BlockState(Orientation.STANDING, 2, 2)
        self.animator.start_roll(block, Direction.RIGHT, duration=0.2, on_complete=on_done)
        self.assertTrue(self.animator.is_animating())
        self.assertEqual(self.animator.state, BlockAnimator.STATE_ROLLING)

        # Update 50%
        self.animator.update(0.1)
        self.assertAlmostEqual(self.animator.progress, 0.5, places=2)
        self.assertFalse(completed)

        # Update to 100%
        self.animator.update(0.15)
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(self.animator.state, BlockAnimator.STATE_IDLE)
        self.assertEqual(completed, [True])

    def test_finish_now(self):
        completed = []
        block = BlockState(Orientation.STANDING, 2, 2)
        self.animator.start_roll(block, Direction.DOWN, duration=0.5, on_complete=lambda: completed.append(1))

        self.animator.finish_now()
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(completed, [1])

    def test_fall_goal(self):
        completed = []
        block = BlockState(Orientation.STANDING, 4, 4)
        self.animator.start_fall_goal(block, (4, 4), duration=0.3, on_complete=lambda: completed.append(True))
        self.assertEqual(self.animator.state, BlockAnimator.STATE_FALL_GOAL)

        self.animator.update(0.35)
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(completed, [True])

    def test_fall_edge(self):
        completed = []
        block = BlockState(Orientation.STANDING, 1, 1)
        self.animator.start_fall_edge(block, Direction.UP, duration=0.4, on_complete=lambda: completed.append(True))
        self.assertEqual(self.animator.state, BlockAnimator.STATE_FALL_EDGE)

        self.animator.update(0.45)
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(completed, [True])

    def test_fall_fragile_and_particles(self):
        completed = []
        block = BlockState(Orientation.STANDING, 2, 3)
        self.animator.start_fall_fragile(block, (2, 3), duration=0.5, on_complete=lambda: completed.append(True))
        self.assertEqual(self.animator.state, BlockAnimator.STATE_FALL_FRAGILE)
        self.assertTrue(len(self.animator.particles) > 0)

        # Update particles
        p_initial_z = self.animator.particles[0].z
        self.animator.update(0.1)
        self.assertNotEqual(self.animator.particles[0].z, p_initial_z)

        # Complete
        self.animator.update(0.45)
        self.assertFalse(self.animator.is_animating())
        self.assertEqual(completed, [True])

    def test_3d_rotation_all_orientations(self):
        # Kiểm tra tính toán hình học 3D không bị lỗi với mọi orientation
        states = [
            BlockState(Orientation.STANDING, 3, 3),
            BlockState(Orientation.HORIZONTAL, 3, 3),
            BlockState(Orientation.VERTICAL, 3, 3),
            BlockState(Orientation.SPLIT, 3, 3, 5, 5, active_cube=0),
            BlockState(Orientation.SPLIT, 3, 3, 5, 5, active_cube=1),
        ]
        for st in states:
            for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
                rmin, rmax, cmin, cmax, zmin, zmax = BlockAnimator._get_box_bounds(st, st.active_cube)
                verts = BlockAnimator._make_cuboid_vertices(rmin, rmax, cmin, cmax, zmin, zmax)
                self.assertEqual(len(verts), 8)
                rotated = BlockAnimator._rotate_box_vertices(verts, d, math.pi / 4, rmin, rmax, cmin, cmax)
                self.assertEqual(len(rotated), 8)
                for pt in rotated:
                    self.assertEqual(len(pt), 3)


if __name__ == "__main__":
    unittest.main()
