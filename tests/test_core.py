"""
Unit test cho phần cốt lõi (theo gợi ý F.Y.I của đề: kiểm thử bảng chuyển hướng sớm).
Chạy:  python -m unittest tests.test_core -v   (từ thư mục Source)
"""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.core import BlockState, Orientation, Direction, GameState
from src.core.map_loader import MapData, SwitchAction

S, H, V = Orientation.STANDING, Orientation.HORIZONTAL, Orientation.VERTICAL
U, D, L, R = Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT


class TestRollTable(unittest.TestCase):
    """12 cặp (hướng khối, hướng lăn) -> (hướng mới, vị trí mới)."""

    def check(self, ori, r, c, d, exp_ori, exp_r, exp_c):
        b = BlockState(ori, r, c).roll(d)
        self.assertEqual((b.orientation, b.r, b.c), (exp_ori, exp_r, exp_c))

    def test_standing(self):
        self.check(S, 5, 5, U, V, 3, 5)
        self.check(S, 5, 5, D, V, 6, 5)
        self.check(S, 5, 5, L, H, 5, 3)
        self.check(S, 5, 5, R, H, 5, 6)

    def test_horizontal(self):
        self.check(H, 5, 5, U, H, 4, 5)
        self.check(H, 5, 5, D, H, 6, 5)
        self.check(H, 5, 5, L, S, 5, 4)
        self.check(H, 5, 5, R, S, 5, 7)

    def test_vertical(self):
        self.check(V, 5, 5, U, S, 4, 5)
        self.check(V, 5, 5, D, S, 7, 5)
        self.check(V, 5, 5, L, V, 5, 4)
        self.check(V, 5, 5, R, V, 5, 6)

    def test_roll_then_back_is_identity(self):
        opp = {U: D, D: U, L: R, R: L}
        for ori in (S, H, V):
            for d in (U, D, L, R):
                b = BlockState(ori, 5, 5)
                self.assertEqual(b.roll(d).roll(opp[d]), b)


def make_map(board, start, goal, switches=None, bridges=()):
    bridges = sorted(bridges)
    idx = {b: i for i, b in enumerate(bridges)}
    init = tuple(board[r][c] != 0 for r, c in bridges)
    return MapData(len(board), len(board[0]), start, goal, board, list(bridges),
                   idx, init, switches or {}, "test")


class TestRules(unittest.TestCase):
    def test_fall_off_and_void(self):
        board = [[1, 1, 1], [1, 1, 1], [1, 1, 9]]
        m = make_map(board, (0, 0), (2, 2))
        st = GameState(BlockState(S, 0, 0), m.initial_bridges, m)
        self.assertIsNone(st.transition(U))
        self.assertIsNone(st.transition(L))
        self.assertIsNotNone(st.transition(R))

    def test_win_only_when_standing(self):
        board = [[1, 1, 1, 1], [1, 1, 1, 9]]
        m = make_map(board, (0, 0), (1, 3))
        lying = GameState(BlockState(H, 1, 2), m.initial_bridges, m)
        standing = GameState(BlockState(S, 1, 3), m.initial_bridges, m)
        self.assertFalse(lying.is_goal())
        self.assertTrue(standing.is_goal())

    def test_fragile_standing_breaks_lying_ok(self):
        board = [[1, 1, 2, 1, 1]]
        m = make_map(board, (0, 0), (0, 4))
        st = GameState(BlockState(S, 0, 0), m.initial_bridges, m)
        # Đứng (0,0) lăn phải -> nằm (0,1),(0,2): nằm trên ô cam => OK
        lying = st.transition(R)
        self.assertIsNotNone(lying)
        # Từ nằm lăn phải -> đứng tại (0,3): ô thường => OK
        self.assertIsNotNone(lying.transition(R))
        # Đứng trên ô cam (0,2) => vỡ
        st2 = GameState(BlockState(H, 0, 0), m.initial_bridges, m)  # chiếm (0,0),(0,1)
        self.assertIsNone(st2.transition(R))  # sẽ đứng tại (0,2) = ô cam

    def test_heavy_switch_needs_standing_soft_does_not(self):
        board = [[1, 1, 1, 1, 1], [1, 1, 3, 1, 5], [1, 0, 1, 1, 1]]
        sw = {
            (1, 2): SwitchAction(3, [], [], [(2, 1)]),   # nặng: mở cầu (2,1)
            (1, 4): SwitchAction(5, [(2, 1)], [], []),   # nhẹ: toggle cầu (2,1)
        }
        m = make_map(board, (1, 1), (2, 4), sw, bridges=[(2, 1)])
        self.assertEqual(m.initial_bridges, (False,))
        # Nằm lên công tắc nặng: KHÔNG kích hoạt
        lying = GameState(BlockState(H, 1, 1), m.initial_bridges, m)  # (1,1),(1,2)
        nxt = lying.transition(U)
        self.assertIsNotNone(nxt)
        # Đứng lên công tắc nặng (1,2): kích hoạt
        st = GameState(BlockState(H, 1, 0), m.initial_bridges, m)  # (1,0),(1,1)
        stand = st.transition(R)  # đứng tại (1,2)
        self.assertEqual((stand.block.orientation, stand.block.r, stand.block.c), (S, 1, 2))
        self.assertEqual(stand.bridge_state, (True,))

    def test_split_merge_and_no_double_toggle(self):
        # Hai khối phân thân; khối 0 bước lên công tắc nhẹ toggle đồng thời sáp nhập với khối 1:
        board = [[1, 1, 1, 1], [1, 5, 1, 1], [1, 1, 1, 0]]
        sw = {(1, 1): SwitchAction(5, [(2, 3)], [], [])}
        m = make_map(board, (0, 0), (2, 2), sw, bridges=[(2, 3)])
        before = m.initial_bridges
        s = GameState(BlockState(Orientation.SPLIT, 1, 0, 1, 3), before, m)
        # khối 0 sang phải -> (1,1) (công tắc); khối 1 ở (1,3): chưa kề nhau
        s1 = s.transition((0, R))
        self.assertEqual(s1.bridge_state, (True,))     # đã toggle đúng 1 lần
        # đưa khối 1 sát lại: (1,3)->(1,2) kề (1,1) => sáp nhập, KHÔNG toggle thêm
        s2 = s1.transition((1, L))
        self.assertEqual(s2.block.orientation, H)
        self.assertEqual(s2.bridge_state, (True,))

    def test_cubes_cannot_overlap(self):
        board = [[1, 1, 1, 1]]
        m = make_map(board, (0, 0), (0, 3))
        s = GameState(BlockState(Orientation.SPLIT, 0, 0, 0, 2), m.initial_bridges, m)
        # Khối 0 sang phải -> (0,1) kề khối 1 (0,2) => sáp nhập (hợp lệ)
        self.assertEqual(s.transition((0, R)).block.orientation, H)


if __name__ == "__main__":
    unittest.main()
