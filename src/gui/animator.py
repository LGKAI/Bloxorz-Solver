"""
Module: animator.py
Mô tả: Quản lý và dựng hình các hiệu ứng chuyển động (Animation) 3D cho khối Bloxorz:
      1. Rolling Animation: Lăn lật 3D 90 độ quanh trục bản lề (pivot edge) trên mặt sàn
         với bóng đổ động (dynamic shadow) và đánh sáng bề mặt 3D chân thực.
      2. Victory Sink Animation: Khối đứng thẳng thụt chìm dần vào lỗ đích phát sáng khi thắng cuộc.
      3. Edge Fall Animation: Khối lật quá đà ra khỏi sàn, mất thăng bằng và rơi tự do
         xoay nhào lộn vào khoảng không hư vô theo gia tốc trọng trường.
      4. Fragile Collapse Animation: Ô cam dễ vỡ nứt sụp, sinh chùm mảnh vỡ hạt (particles)
         và khối rơi thẳng đứng xuống vực sâu.
"""

import math
import random
try:
    import pygame
except ImportError:
    pygame = None

from typing import List, Tuple, Optional, Any, Callable

from src.core.block import BlockState, Orientation, Direction
from src.gui.renderer import (
    COLOR_BLOCK_TOP,
    COLOR_BLOCK_LEFT,
    COLOR_BLOCK_RIGHT,
    COLOR_BLOCK_EDGE,
    COLOR_SHADOW,
    COLOR_CUBE0_TOP,
    COLOR_CUBE0_LEFT,
    COLOR_CUBE0_RIGHT,
    COLOR_CUBE1_TOP,
    COLOR_CUBE1_LEFT,
    COLOR_CUBE1_RIGHT,
    COLOR_FRAGILE_TOP,
    COLOR_FRAGILE_LEFT,
    COLOR_FRAGILE_RIGHT,
)


class Particle:
    """Hạt mảnh vỡ sàn cam khi ô bị nứt sập."""
    def __init__(self, r: float, c: float, z: float):
        self.r = r
        self.c = c
        self.z = z
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(0.8, 2.5)
        self.vr = math.cos(angle) * speed
        self.vc = math.sin(angle) * speed
        self.vz = random.uniform(1.0, 3.5)  # Văng lên nhẹ rồi rơi xuống
        self.size = random.randint(2, 5)
        self.color = random.choice([COLOR_FRAGILE_TOP, COLOR_FRAGILE_LEFT, (255, 180, 80)])
        self.life = 1.0  # Từ 1.0 giảm về 0.0

    def update(self, dt: float):
        self.r += self.vr * dt
        self.c += self.vc * dt
        self.z += self.vz * dt
        self.vz -= 9.8 * dt  # Trọng lực kéo xuống
        self.life -= dt * 1.5


class BlockAnimator:
    """
    Quản lý trạng thái và tính toán hình học 3D cho toàn bộ animation của khối Bloxorz.
    """

    STATE_IDLE = "IDLE"
    STATE_ROLLING = "ROLLING"
    STATE_FALL_GOAL = "FALL_GOAL"
    STATE_FALL_EDGE = "FALL_EDGE"
    STATE_FALL_FRAGILE = "FALL_FRAGILE"

    def __init__(self):
        self.state = self.STATE_IDLE
        self.progress = 0.0          # Tiến trình [0.0, 1.0]
        self.duration = 0.16         # Thời lượng tính bằng giây
        self.elapsed = 0.0

        # Dữ liệu khối cho animation
        self.block: Optional[BlockState] = None
        self.direction: Optional[Direction] = None
        self.cube_index: int = 0
        self.next_game_state: Any = None
        self.on_complete: Optional[Callable[[], None]] = None

        # Hiệu ứng phụ
        self.particles: List[Particle] = []
        self.fragile_cell: Optional[Tuple[int, int]] = None
        self.goal_cell: Optional[Tuple[int, int]] = None

    def is_animating(self) -> bool:
        """Kiểm tra có animation nào đang chạy hay không."""
        return self.state != self.STATE_IDLE

    def reset(self):
        """Hủy bỏ toàn bộ animation hiện tại và đưa về trạng thái nghỉ."""
        self.state = self.STATE_IDLE
        self.progress = 0.0
        self.elapsed = 0.0
        self.block = None
        self.direction = None
        self.next_game_state = None
        self.on_complete = None
        self.particles.clear()
        self.fragile_cell = None
        self.goal_cell = None

    def finish_now(self):
        """Hoàn tất ngay animation hiện tại (snap to end) để không bị nghẽn input phím."""
        if self.state != self.STATE_IDLE and self.on_complete:
            callback = self.on_complete
            self.reset()
            callback()
        else:
            self.reset()

    def start_roll(
        self,
        block: BlockState,
        direction: Direction,
        cube_index: int = 0,
        duration: float = 0.15,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """Kích hoạt animation lăn khối 90 độ quanh mép."""
        self.state = self.STATE_ROLLING
        self.block = block
        self.direction = direction
        self.cube_index = cube_index
        self.duration = max(0.06, duration)
        self.elapsed = 0.0
        self.progress = 0.0
        self.on_complete = on_complete

    def start_fall_goal(
        self,
        block: BlockState,
        goal_cell: Tuple[int, int],
        duration: float = 0.8,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """Kích hoạt animation thụt chìm vào lỗ đích khi thắng cuộc."""
        self.state = self.STATE_FALL_GOAL
        self.block = block
        self.goal_cell = goal_cell
        self.duration = duration
        self.elapsed = 0.0
        self.progress = 0.0
        self.on_complete = on_complete

    def start_fall_edge(
        self,
        block: BlockState,
        direction: Direction,
        cube_index: int = 0,
        duration: float = 0.65,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """Kích hoạt animation lật quá mép và rơi tự do vào vực thẳm."""
        self.state = self.STATE_FALL_EDGE
        self.block = block
        self.direction = direction
        self.cube_index = cube_index
        self.duration = duration
        self.elapsed = 0.0
        self.progress = 0.0
        self.on_complete = on_complete

    def start_fall_fragile(
        self,
        block: BlockState,
        fragile_cell: Tuple[int, int],
        duration: float = 0.7,
        on_complete: Optional[Callable[[], None]] = None
    ):
        """Kích hoạt animation nứt sụp ô cam và rơi thẳng xuống vực."""
        self.state = self.STATE_FALL_FRAGILE
        self.block = block
        self.fragile_cell = fragile_cell
        self.duration = duration
        self.elapsed = 0.0
        self.progress = 0.0
        self.on_complete = on_complete

        # Khởi tạo các hạt mảnh vỡ cam văng ra
        self.particles.clear()
        fr, fc = fragile_cell
        for _ in range(18):
            self.particles.append(Particle(fr + random.uniform(-0.3, 0.3), fc + random.uniform(-0.3, 0.3), 0.1))

    def update(self, dt: float):
        """Cập nhật tiến trình thời gian và trạng thái animation mỗi frame."""
        if self.state == self.STATE_IDLE:
            return

        self.elapsed += dt
        self.progress = min(1.0, self.elapsed / self.duration)

        # Cập nhật particles nếu có
        if self.particles:
            for p in self.particles:
                p.update(dt)
            self.particles = [p for p in self.particles if p.life > 0.0]

        # Kiểm tra khi animation hoàn tất
        if self.progress >= 1.0:
            callback = self.on_complete
            self.reset()
            if callback:
                callback()

    # =========================================================================
    # CÁC PHÉP BIẾN ĐỔI HÌNH HỌC 3D VÀ CHIẾU ISOMETRIC
    # =========================================================================

    @staticmethod
    def _get_box_bounds(block: BlockState, cube_idx: int = 0) -> Tuple[float, float, float, float, float, float]:
        """
        Trả về hộp giới hạn (rmin, rmax, cmin, cmax, zmin, zmax) trong không gian lưới.
        """
        ori = block.orientation
        if ori == Orientation.STANDING:
            return (block.r - 0.5, block.r + 0.5, block.c - 0.5, block.c + 0.5, 0.0, 2.0)
        elif ori == Orientation.HORIZONTAL:
            # Chiếm (r, c) và (r, c + 1)
            return (block.r - 0.5, block.r + 0.5, block.c - 0.5, block.c + 1.5, 0.0, 1.0)
        elif ori == Orientation.VERTICAL:
            # Chiếm (r, c) và (r + 1, c)
            return (block.r - 0.5, block.r + 1.5, block.c - 0.5, block.c + 0.5, 0.0, 1.0)
        elif ori == Orientation.SPLIT:
            cr = block.r if cube_idx == 0 else block.r1
            cc = block.c if cube_idx == 0 else block.c1
            return (cr - 0.5, cr + 0.5, cc - 0.5, cc + 0.5, 0.0, 1.0)
        return (0, 0, 0, 0, 0, 0)

    @staticmethod
    def _make_cuboid_vertices(rmin: float, rmax: float, cmin: float, cmax: float, zmin: float, zmax: float):
        """Tạo danh sách 8 đỉnh của hình hộp chữ nhật."""
        return [
            (rmin, cmin, zmin),  # 0
            (rmax, cmin, zmin),  # 1
            (rmax, cmax, zmin),  # 2
            (rmin, cmax, zmin),  # 3
            (rmin, cmin, zmax),  # 4
            (rmax, cmin, zmax),  # 5
            (rmax, cmax, zmax),  # 6
            (rmin, cmax, zmax),  # 7
        ]

    @staticmethod
    def _rotate_box_vertices(
        verts: List[Tuple[float, float, float]],
        direction: Direction,
        theta: float,
        rmin: float, rmax: float, cmin: float, cmax: float
    ) -> List[Tuple[float, float, float]]:
        """
        Quay 8 đỉnh quanh trục bản lề (pivot edge) trên mặt sàn (z = 0) theo hướng lăn.
        """
        cos_t = math.cos(theta)
        sin_t = math.sin(theta)
        res = []

        for r, c, z in verts:
            if direction == Direction.RIGHT:
                dc = c - cmax
                dc_new = dc * cos_t + z * sin_t
                z_new = -dc * sin_t + z * cos_t
                res.append((r, cmax + dc_new, z_new))
            elif direction == Direction.LEFT:
                dc = c - cmin
                dc_new = dc * cos_t - z * sin_t
                z_new = dc * sin_t + z * cos_t
                res.append((r, cmin + dc_new, z_new))
            elif direction == Direction.DOWN:
                dr = r - rmax
                dr_new = dr * cos_t + z * sin_t
                z_new = -dr * sin_t + z * cos_t
                res.append((rmax + dr_new, c, z_new))
            elif direction == Direction.UP:
                dr = r - rmin
                dr_new = dr * cos_t - z * sin_t
                z_new = dr * sin_t + z * cos_t
                res.append((rmin + dr_new, c, z_new))
            else:
                res.append((r, c, z))

        return res

    @staticmethod
    def _iso_project(
        r: float, c: float, z: float,
        origin_x: int, origin_y: int,
        tile_w: int, tile_h: int, block_unit_h: int
    ) -> Tuple[int, int]:
        """Chiếu điểm (r, c, z) 3D sang tọa độ màn hình Isometric (x, y)."""
        x = origin_x + (c - r) * (tile_w / 2.0)
        y = origin_y + (c + r) * (tile_h / 2.0) - z * block_unit_h
        return (int(x), int(y))

    @staticmethod
    def _polygon_signed_area_2d(pts: List[Tuple[int, int]]) -> float:
        """Tính diện tích có hướng 2D để lọc mặt nhìn thấy (Back-face Culling)."""
        area = 0.0
        n = len(pts)
        for i in range(n):
            x1, y1 = pts[i]
            x2, y2 = pts[(i + 1) % n]
            area += (x1 * y2 - x2 * y1)
        return area / 2.0

    @staticmethod
    def _compute_face_normal(pts3d: List[Tuple[float, float, float]]) -> Tuple[float, float, float]:
        """Tính vector pháp tuyến ngoài của mặt đa giác 3D."""
        p0, p1, p2, p3 = pts3d
        v1 = (p1[0] - p0[0], p1[1] - p0[1], p1[2] - p0[2])
        v2 = (p3[0] - p0[0], p3[1] - p0[1], p3[2] - p0[2])
        nr = v1[1] * v2[2] - v1[2] * v2[1]
        nc = v1[2] * v2[0] - v1[0] * v2[2]
        nz = v1[0] * v2[1] - v1[1] * v2[0]
        length = math.sqrt(nr * nr + nc * nc + nz * nz)
        if length < 1e-6:
            return (0.0, 0.0, 1.0)
        return (nr / length, nc / length, nz / length)

    def _render_3d_box(
        self,
        surface: Any,
        verts3d: List[Tuple[float, float, float]],
        origin_x: int, origin_y: int,
        tile_w: int, tile_h: int, block_unit_h: int,
        is_cube0: bool = False, is_cube1: bool = False,
        draw_shadow: bool = True
    ):
        """
        Vẽ một hình hộp 3D tùy ý xác định bởi 8 đỉnh với đổ bóng và đổ màu chuẩn xác.
        """
        if not pygame or surface is None:
            return

        # Chiếu 8 đỉnh sang 2D
        pts2d = [
            self._iso_project(r, c, z, origin_x, origin_y, tile_w, tile_h, block_unit_h)
            for r, c, z in verts3d
        ]

        # 1. Vẽ bóng đổ động trên mặt sàn (z = 0) nếu đáy khối còn gần mặt sàn
        if draw_shadow:
            shadow_z = 0.0
            shadow_pts = []
            for i in [0, 1, 2, 3]:
                r, c, _ = verts3d[i]
                shadow_pts.append(self._iso_project(r, c, shadow_z, origin_x, origin_y, tile_w, tile_h, block_unit_h))
            if abs(self._polygon_signed_area_2d(shadow_pts)) > 1.0:
                shadow_surf = pygame.Surface((tile_w * 4, tile_h * 4), pygame.SRCALPHA)
                min_sx = min(p[0] for p in shadow_pts)
                min_sy = min(p[1] for p in shadow_pts)
                rel_pts = [(p[0] - min_sx + 10, p[1] - min_sy + 10) for p in shadow_pts]
                pygame.draw.polygon(shadow_surf, COLOR_SHADOW, rel_pts)
                surface.blit(shadow_surf, (min_sx - 10, min_sy - 10))

        # 6 mặt của khối
        faces_def = [
            ("top", [4, 7, 6, 5]),
            ("bottom", [0, 1, 2, 3]),
            ("front_r", [1, 5, 6, 2]),
            ("back_r", [0, 3, 7, 4]),
            ("right_c", [2, 6, 7, 3]),
            ("left_c", [0, 4, 5, 1])
        ]

        # Bảng màu
        if is_cube0:
            col_top, col_left, col_right = COLOR_CUBE0_TOP, COLOR_CUBE0_LEFT, COLOR_CUBE0_RIGHT
        elif is_cube1:
            col_top, col_left, col_right = COLOR_CUBE1_TOP, COLOR_CUBE1_LEFT, COLOR_CUBE1_RIGHT
        else:
            col_top, col_left, col_right = COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_RIGHT

        # Lọc các mặt nhìn thấy được (area > 1e-4) và sắp xếp theo Painter's Algorithm
        visible_faces = []
        for name, indices in faces_def:
            face_pts2d = [pts2d[i] for i in indices]
            area = self._polygon_signed_area_2d(face_pts2d)
            if area > 1e-4:
                pts_for_face = [verts3d[i] for i in indices]
                cr = sum(p[0] for p in pts_for_face) / 4.0
                cc = sum(p[1] for p in pts_for_face) / 4.0
                cz = sum(p[2] for p in pts_for_face) / 4.0
                depth = (cr + cc) + cz * 0.1
                normal = self._compute_face_normal(pts_for_face)
                visible_faces.append((depth, name, face_pts2d, normal))

        visible_faces.sort(key=lambda item: item[0])

        for _, name, face_pts2d, normal in visible_faces:
            nr, nc, nz = normal

            if nz > 0.35:
                base_col = col_top
            elif nc > 0.35:
                base_col = col_right
            elif nr > 0.35:
                base_col = col_left
            elif nz < -0.35:
                base_col = tuple(max(0, int(c * 0.55)) for c in col_top)
            else:
                base_col = tuple(max(0, int(c * 0.65)) for c in col_left)

            light_dot = max(0.0, -nr * 0.3 + nc * 0.4 + nz * 0.8)
            shade_factor = 0.75 + 0.25 * light_dot
            final_col = (
                min(255, int(base_col[0] * shade_factor)),
                min(255, int(base_col[1] * shade_factor)),
                min(255, int(base_col[2] * shade_factor))
            )

            pygame.draw.polygon(surface, final_col, face_pts2d)
            pygame.draw.lines(surface, COLOR_BLOCK_EDGE, True, face_pts2d, 1)

    # =========================================================================
    # HÀM RENDER CHÍNH CHO TỪNG LOẠI ANIMATION
    # =========================================================================

    def render(
        self,
        surface: Any,
        origin_x: int,
        origin_y: int,
        tile_w: int,
        tile_h: int,
        block_unit_h: int
    ):
        """Vẽ khung hình animation hiện tại của khối Bloxorz."""
        if self.state == self.STATE_IDLE or self.block is None:
            return

        p = self.progress

        if self.state == self.STATE_ROLLING:
            self._render_rolling(surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p)
        elif self.state == self.STATE_FALL_GOAL:
            self._render_fall_goal(surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p)
        elif self.state == self.STATE_FALL_EDGE:
            self._render_fall_edge(surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p)
        elif self.state == self.STATE_FALL_FRAGILE:
            self._render_fall_fragile(surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p)

    def _render_rolling(self, surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p: float):
        """Dựng hình khối đang lăn lật 3D 90 độ."""
        t_eased = p * p * (3.0 - 2.0 * p)
        theta = t_eased * (math.pi / 2.0)

        ori = self.block.orientation

        if ori != Orientation.SPLIT:
            rmin, rmax, cmin, cmax, zmin, zmax = self._get_box_bounds(self.block)
            verts = self._make_cuboid_vertices(rmin, rmax, cmin, cmax, zmin, zmax)
            rotated = self._rotate_box_vertices(verts, self.direction, theta, rmin, rmax, cmin, cmax)
            self._render_3d_box(surface, rotated, origin_x, origin_y, tile_w, tile_h, block_unit_h)
        else:
            active_idx = self.cube_index
            other_idx = 1 - active_idx

            other_rmin, other_rmax, other_cmin, other_cmax, other_zmin, other_zmax = self._get_box_bounds(self.block, other_idx)
            other_verts = self._make_cuboid_vertices(other_rmin, other_rmax, other_cmin, other_cmax, other_zmin, other_zmax)

            act_rmin, act_rmax, act_cmin, act_cmax, act_zmin, act_zmax = self._get_box_bounds(self.block, active_idx)
            act_verts = self._make_cuboid_vertices(act_rmin, act_rmax, act_cmin, act_cmax, act_zmin, act_zmax)
            act_rotated = self._rotate_box_vertices(act_verts, self.direction, theta, act_rmin, act_rmax, act_cmin, act_cmax)

            act_center_depth = (act_rmin + act_cmin)
            other_center_depth = (other_rmin + other_cmin)

            if other_center_depth < act_center_depth:
                self._render_3d_box(surface, other_verts, origin_x, origin_y, tile_w, tile_h, block_unit_h,
                                    is_cube0=(other_idx == 0), is_cube1=(other_idx == 1))
                self._render_3d_box(surface, act_rotated, origin_x, origin_y, tile_w, tile_h, block_unit_h,
                                    is_cube0=(active_idx == 0), is_cube1=(active_idx == 1))
            else:
                self._render_3d_box(surface, act_rotated, origin_x, origin_y, tile_w, tile_h, block_unit_h,
                                    is_cube0=(active_idx == 0), is_cube1=(active_idx == 1))
                self._render_3d_box(surface, other_verts, origin_x, origin_y, tile_w, tile_h, block_unit_h,
                                    is_cube0=(other_idx == 0), is_cube1=(other_idx == 1))

    def _render_fall_goal(self, surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p: float):
        """Khối chìm sâu dần thẳng đứng vào lòng lỗ đích phát sáng và biến mất hoàn toàn."""
        if p >= 0.90:
            return  # Khối đã rớt đủ sâu và biến mất hoàn toàn

        rmin, rmax, cmin, cmax, zmin, zmax = self._get_box_bounds(self.block)
        # Rơi nhanh dần theo trọng lực xuống sâu dưới mặt sàn (đáy chìm xuống -5.0, đỉnh chìm xuống -3.0)
        z_offset = -5.0 * (p ** 1.6)

        # Thu nhỏ khối dần vào tâm miệng lỗ đích khi chìm sâu (hiệu ứng hút sâu vào hố)
        scale = max(0.1, 1.0 - (p ** 1.3) * 0.7)
        mid_r = (rmin + rmax) / 2.0
        mid_c = (cmin + cmax) / 2.0
        s_rmin = mid_r + (rmin - mid_r) * scale
        s_rmax = mid_r + (rmax - mid_r) * scale
        s_cmin = mid_c + (cmin - mid_c) * scale
        s_cmax = mid_c + (cmax - mid_c) * scale

        verts = self._make_cuboid_vertices(s_rmin, s_rmax, s_cmin, s_cmax, zmin + z_offset, zmax + z_offset)
        self._render_3d_box(surface, verts, origin_x, origin_y, tile_w, tile_h, block_unit_h, draw_shadow=False)

    def _render_fall_edge(self, surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p: float):
        """Khối lật nghiêng ra mép rồi rơi tự do xoay vòng xuống vực thẳm."""
        rmin, rmax, cmin, cmax, zmin, zmax = self._get_box_bounds(self.block, self.cube_index)
        verts = self._make_cuboid_vertices(rmin, rmax, cmin, cmax, zmin, zmax)

        if p < 0.35:
            local_t = p / 0.35
            theta = local_t * (math.pi / 3.0)
            rotated = self._rotate_box_vertices(verts, self.direction, theta, rmin, rmax, cmin, cmax)
            self._render_3d_box(surface, rotated, origin_x, origin_y, tile_w, tile_h, block_unit_h)
        else:
            t_fall = (p - 0.35) / 0.65
            theta = (math.pi / 3.0) + t_fall * math.pi * 0.8
            z_fall = -12.0 * (t_fall ** 2)

            dr_drift, dc_drift = 0.0, 0.0
            drift_dist = t_fall * 1.5
            if self.direction == Direction.UP:
                dr_drift = -drift_dist
            elif self.direction == Direction.DOWN:
                dr_drift = drift_dist
            elif self.direction == Direction.LEFT:
                dc_drift = -drift_dist
            elif self.direction == Direction.RIGHT:
                dc_drift = drift_dist

            base_rotated = self._rotate_box_vertices(verts, self.direction, theta, rmin, rmax, cmin, cmax)
            fallen_verts = [
                (r + dr_drift, c + dc_drift, z + z_fall)
                for r, c, z in base_rotated
            ]
            self._render_3d_box(surface, fallen_verts, origin_x, origin_y, tile_w, tile_h, block_unit_h, draw_shadow=False)

    def _render_fall_fragile(self, surface, origin_x, origin_y, tile_w, tile_h, block_unit_h, p: float):
        """Khối rơi thẳng đứng khi ô cam bị nứt sập."""
        rmin, rmax, cmin, cmax, zmin, zmax = self._get_box_bounds(self.block)
        z_fall = -10.0 * (p ** 2)
        tilt = math.sin(p * 20.0) * 0.05 * (1.0 - p)
        verts = [
            (r + tilt, c - tilt, z + z_fall)
            for r, c, z in self._make_cuboid_vertices(rmin, rmax, cmin, cmax, zmin, zmax)
        ]
        self._render_3d_box(surface, verts, origin_x, origin_y, tile_w, tile_h, block_unit_h, draw_shadow=False)

    def render_overlays(
        self,
        surface: Any,
        origin_x: int,
        origin_y: int,
        tile_w: int,
        tile_h: int,
        block_unit_h: int
    ):
        """
        Vẽ các hiệu ứng phụ bề mặt (hạt bụi cam nứt vỡ, quầng sáng đích bùng nổ).
        """
        if not pygame or surface is None:
            return

        # 1. Vẽ quầng sáng đích khi thắng cuộc
        if self.state == self.STATE_FALL_GOAL and self.goal_cell:
            gr, gc = self.goal_cell
            gx, gy = self._iso_project(gr, gc, 0.0, origin_x, origin_y, tile_w, tile_h, block_unit_h)
            flare_radius = int(tile_w // 2 + math.sin(self.progress * math.pi) * 22)
            if flare_radius > 0:
                glow_surf = pygame.Surface((flare_radius * 2 + 10, flare_radius + 10), pygame.SRCALPHA)
                alpha = int(180 * math.sin(self.progress * math.pi))
                pygame.draw.ellipse(
                    glow_surf,
                    (255, 230, 80, alpha),
                    (5, 5, flare_radius * 2, flare_radius)
                )
                surface.blit(glow_surf, (gx - flare_radius - 5, gy - flare_radius // 2 - 5))

        # 2. Vẽ các hạt mảnh vỡ cam
        if self.particles:
            for pt in self.particles:
                px, py = self._iso_project(pt.r, pt.c, max(0.0, pt.z), origin_x, origin_y, tile_w, tile_h, block_unit_h)
                alpha_val = int(255 * pt.life)
                particle_surf = pygame.Surface((pt.size * 2, pt.size * 2), pygame.SRCALPHA)
                pygame.draw.circle(
                    particle_surf,
                    (pt.color[0], pt.color[1], pt.color[2], alpha_val),
                    (pt.size, pt.size),
                    pt.size
                )
                surface.blit(particle_surf, (px - pt.size, py - pt.size))
