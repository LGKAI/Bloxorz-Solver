"""
Module: renderer.py
Mô tả: Bộ dựng hình đồ họa 3D Isometric chuẩn phong cách game Bloxorz kinh điển.
      - Chiếu ma trận (row, col) thành không gian 3D nghiêng theo đúng góc nhìn của game gốc:
        Trục cột c hơi chếch lên bên phải, trục hàng r chếch xuống bên phải,
        khối đứng cao ráo và bóng đổ mềm mờ (soft blurred shadow) phía sau.
      - Render mặt phẳng sàn liền mạch: 2 ô gạch chạm nhau không vẽ các cạnh đổ bóng hông,
        chỉ mép ngoài tiếp giáp với vực thẳm mới có độ dày 3D.
      - Hỗ trợ depth filtering để các ô sàn phía trước che khuất nhân vật khi nhân vật rơi xuống vực.
      - Tự động co giãn (Adaptive scaling) và căn giữa bản đồ chuẩn xác cho mọi màn chơi.
      - Nền gradient đỏ rực rỡ đặc trưng của Bloxorz.
"""

import pygame
import math
from typing import Tuple, List, Optional
from src.core.block import BlockState, Orientation
from src.core.map_loader import MapData
from src.gui.safe_font import get_safe_font, SafeFont


# =========================================================================
# BẢNG MÀU CHUẨN GỐC BLOXORZ (Classic Authentic Palette)
# =========================================================================

# Nền gradient đỏ đặc trưng của Bloxorz
COLOR_BG_GRAD_TOP = (185, 28, 0)
COLOR_BG_GRAD_MID = (80, 5, 0)
COLOR_BG_GRAD_BOT = (18, 1, 1)

# Màu ô sàn gạch bê tông xám sáng (Classic Slate Tiles)
COLOR_TILE_TOP = (196, 206, 215)
COLOR_TILE_LEFT = (130, 140, 150)
COLOR_TILE_RIGHT = (105, 115, 125)  # Mặt trước hướng về người nhìn
COLOR_TILE_FRONT = COLOR_TILE_RIGHT
COLOR_TILE_BORDER = (160, 172, 182)

# Ô cam dễ vỡ (Fragile tile)
COLOR_FRAGILE_TOP = (235, 120, 45)
COLOR_FRAGILE_LEFT = (180, 85, 25)
COLOR_FRAGILE_RIGHT = (150, 65, 15)
COLOR_FRAGILE_FRONT = COLOR_FRAGILE_RIGHT

# Cầu mở (Bridge open - màu đồng sáng)
COLOR_BRIDGE_OPEN_TOP = (220, 175, 60)
COLOR_BRIDGE_OPEN_LEFT = (175, 135, 40)
COLOR_BRIDGE_OPEN_RIGHT = (145, 105, 25)
COLOR_BRIDGE_OPEN_FRONT = COLOR_BRIDGE_OPEN_RIGHT

# Cầu đóng (Khung nét đứt trên vực sâu)
COLOR_BRIDGE_CLOSED_OUTLINE = (65, 30, 25)

# Lỗ đích (Goal Hole sâu hút vào lòng đất)
COLOR_GOAL_CORE = (15, 18, 22)
COLOR_GOAL_INNER_BACK = (55, 45, 30)
COLOR_GOAL_INNER_RIGHT = (35, 28, 20)
COLOR_GOAL_BORDER = (90, 80, 55)

# Khối Bloxorz cổ điển (Nâu đồng / Thép gỉ / Kim loại quý vân sáng)
COLOR_BLOCK_TOP = (168, 122, 108)
COLOR_BLOCK_LEFT = (72, 60, 68)
COLOR_BLOCK_RIGHT = (110, 78, 68)
COLOR_BLOCK_FRONT = COLOR_BLOCK_RIGHT
COLOR_BLOCK_EDGE = (195, 150, 135)

COLOR_SHADOW = (0, 0, 0, 95)

# Khối phân thân Split (Xanh dương / Tím phát sáng)
COLOR_CUBE0_TOP = (70, 185, 235)
COLOR_CUBE0_LEFT = (35, 130, 180)
COLOR_CUBE0_RIGHT = (48, 155, 205)
COLOR_CUBE0_FRONT = COLOR_CUBE0_RIGHT

COLOR_CUBE1_TOP = (215, 105, 235)
COLOR_CUBE1_LEFT = (155, 65, 185)
COLOR_CUBE1_RIGHT = (180, 80, 205)
COLOR_CUBE1_FRONT = COLOR_CUBE1_RIGHT


# Vector cơ sở chuẩn hóa từ ảnh gốc Bloxorz:
U_BASE_X = 1.0
U_BASE_Y = -0.1585
V_BASE_X = 0.2559
V_BASE_Y = 0.3779
H_BASE = 0.647
D_BASE = 0.132


def draw_soft_shadow(surface: pygame.Surface, pts: List[Tuple[int, int]], base_alpha: int = 90):
    """
    Vẽ bóng đổ có độ mờ nhẹ (feathered / blurred soft shadow) bằng kỹ thuật smoothscale down & up.
    """
    if len(pts) < 3 or surface is None:
        return

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    pad = 12
    w = (max_x - min_x) + pad * 2
    h = (max_y - min_y) + pad * 2
    if w <= 0 or h <= 0:
        return

    shadow_surf = pygame.Surface((w, h), pygame.SRCALPHA)
    rel_pts = [(p[0] - min_x + pad, p[1] - min_y + pad) for p in pts]
    pygame.draw.polygon(shadow_surf, (0, 0, 0, max(10, min(255, base_alpha))), rel_pts)

    # Downscale và Upscale nội suy bilinear tạo viền mờ mềm mại
    dw = max(4, w // 4)
    dh = max(4, h // 4)
    small = pygame.transform.smoothscale(shadow_surf, (dw, dh))
    blurred = pygame.transform.smoothscale(small, (w, h))

    surface.blit(blurred, (min_x - pad, min_y - pad))


class IsoRenderer:
    """
    Trình dựng hình đồ họa 3D Isometric theo góc nhìn chuẩn của Bloxorz gốc.
    """

    def __init__(self, screen, tile_width: int = 68, tile_height: int = 44, tile_depth: int = 9):
        self.screen = screen
        self.scale = 65.0

        # Vector chuyển đổi màn hình (px)
        self.ux = U_BASE_X * self.scale
        self.uy = U_BASE_Y * self.scale
        self.vx = V_BASE_X * self.scale
        self.vy = V_BASE_Y * self.scale
        self.bh = H_BASE * self.scale
        self.tile_d = max(5, int(D_BASE * self.scale))

        # Thuộc tính tương thích ngược
        self.tile_w = int(self.ux)
        self.tile_h = int(self.vy * 2)
        self.block_unit_h = int(self.bh)

        self.origin_x = 410
        self.origin_y = 380

        # Bề mặt đệm vẽ nền gradient
        self._bg_surface: Optional[pygame.Surface] = None
        self._bg_size: Tuple[int, int] = (0, 0)

        # Khởi tạo font chữ cho các biểu tượng công tắc
        self.font_small = get_safe_font("segoeui", 13, bold=True)
        self.font_bold = get_safe_font("segoeui", 15, bold=True)

    def compute_layout(self, map_data: MapData, view_w: int = 820, view_h: int = 780) -> Tuple[int, int]:
        """
        Tính toán tỷ lệ scale và vị trí origin_x, origin_y tối ưu cho từng bản đồ,
        giúp bàn cờ luôn hiển thị to, đẹp và cân đối hoàn hảo trong khung view_w x view_h.
        """
        pts = []
        for r in range(map_data.rows):
            for c in range(map_data.cols):
                if map_data.board[r][c] != 0 or (r, c) in map_data.bridge_indices:
                    for dr, dc in [(0, 0), (0, 1), (1, 1), (1, 0)]:
                        gx = (c + dc) * U_BASE_X + (r + dr) * V_BASE_X
                        gy = (c + dc) * U_BASE_Y + (r + dr) * V_BASE_Y
                        pts.append((gx, gy))

        if not pts:
            return (self.origin_x, self.origin_y)

        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)

        unscaled_w = max_x - min_x
        unscaled_h = max_y - min_y

        target_w = max(200.0, float(view_w - 90))
        target_h = max(200.0, float(view_h - 220))

        scale_w = target_w / max(0.1, unscaled_w)
        scale_h = target_h / max(0.1, unscaled_h)
        self.scale = max(38.0, min(scale_w, scale_h, 68.0))

        # Cập nhật các vector theo scale mới
        self.ux = U_BASE_X * self.scale
        self.uy = U_BASE_Y * self.scale
        self.vx = V_BASE_X * self.scale
        self.vy = V_BASE_Y * self.scale
        self.bh = H_BASE * self.scale
        self.tile_d = max(5, int(D_BASE * self.scale))

        self.tile_w = int(self.ux)
        self.tile_h = int(self.vy * 2)
        self.block_unit_h = int(self.bh)

        scaled_min_x = min_x * self.scale
        scaled_max_x = max_x * self.scale
        scaled_min_y = min_y * self.scale
        scaled_max_y = max_y * self.scale

        self.origin_x = int((view_w - (scaled_max_x - scaled_min_x)) / 2.0 - scaled_min_x)
        self.origin_y = int((view_h - (scaled_max_y - scaled_min_y)) / 2.0 - scaled_min_y + 40)

        return (self.origin_x, self.origin_y)

    def grid_to_iso(
        self,
        r: float,
        c: float,
        origin_x: Optional[int] = None,
        origin_y: Optional[int] = None,
        z: float = 0.0
    ) -> Tuple[int, int]:
        """Chuyển đổi tọa độ 3D ma trận (row, col, z) sang tọa độ màn hình (x, y)."""
        ox = self.origin_x if origin_x is None else origin_x
        oy = self.origin_y if origin_y is None else origin_y
        x = ox + c * self.ux + r * self.vx
        y = oy + c * self.uy + r * self.vy - z * self.bh
        return (int(x), int(y))

    @staticmethod
    def calc_depth(r: float, c: float) -> float:
        """
        Tính toán độ sâu (depth) thực tế trong không gian 3D Isometric chuẩn Bloxorz.
        Hệ số dựa trên vector cơ sở: V_BASE_Y = 0.3779 và U_BASE_Y = -0.1585.
        Tăng r làm tăng depth (tiến về phía gần người nhìn).
        Giảm c làm tăng depth (tiến về phía gần người nhìn ở bên trái).
        """
        return r * 3779.0 - c * 1585.0

    def render_background(self, surface: pygame.Surface, width: int = 820, height: int = 780):
        """Vẽ nền dải gradient đỏ huyền thoại của Bloxorz."""
        if self._bg_surface is None or self._bg_size != (width, height):
            self._bg_surface = pygame.Surface((width, height))
            self._bg_size = (width, height)
            for y in range(height):
                t = y / float(height)
                if t < 0.48:
                    lt = t / 0.48
                    r = int(COLOR_BG_GRAD_TOP[0] * (1 - lt) + COLOR_BG_GRAD_MID[0] * lt)
                    g = int(COLOR_BG_GRAD_TOP[1] * (1 - lt) + COLOR_BG_GRAD_MID[1] * lt)
                    b = int(COLOR_BG_GRAD_TOP[2] * (1 - lt) + COLOR_BG_GRAD_MID[2] * lt)
                else:
                    lt = (t - 0.48) / 0.52
                    r = int(COLOR_BG_GRAD_MID[0] * (1 - lt) + COLOR_BG_GRAD_BOT[0] * lt)
                    g = int(COLOR_BG_GRAD_MID[1] * (1 - lt) + COLOR_BG_GRAD_BOT[1] * lt)
                    b = int(COLOR_BG_GRAD_MID[2] * (1 - lt) + COLOR_BG_GRAD_BOT[2] * lt)
                pygame.draw.line(self._bg_surface, (r, g, b), (0, y), (width, y))

        surface.blit(self._bg_surface, (0, 0))

    def draw_iso_tile(
        self,
        surface: pygame.Surface,
        r: int,
        c: int,
        origin_x: int,
        origin_y: int,
        top_color: Tuple[int, int, int],
        left_color: Tuple[int, int, int],
        front_color: Tuple[int, int, int],
        depth: Optional[int] = None,
        draw_border: bool = True,
        z_offset_px: int = 0,
        draw_left: bool = True,
        draw_front: bool = True
    ):
        """
        Vẽ một ô sàn 3D. Chỉ vẽ mặt hông trái/trước khi mép đó tiếp giáp với vực thẳm
        (2 ô gạch chạm nhau trên cùng mặt phẳng thì không vẽ bóng đổ gờ nổi).
        """
        d = self.tile_d if depth is None else depth

        # 4 đỉnh của mặt trên ô sàn tại ô (r, c)
        p0 = self.grid_to_iso(r, c, origin_x, origin_y)
        p1 = self.grid_to_iso(r, c + 1, origin_x, origin_y)
        p2 = self.grid_to_iso(r + 1, c + 1, origin_x, origin_y)
        p3 = self.grid_to_iso(r + 1, c, origin_x, origin_y)

        if z_offset_px != 0:
            p0 = (p0[0], p0[1] + z_offset_px)
            p1 = (p1[0], p1[1] + z_offset_px)
            p2 = (p2[0], p2[1] + z_offset_px)
            p3 = (p3[0], p3[1] + z_offset_px)

        if d > 0:
            # Mặt hông trái: từ p0 sang p3 (chỉ vẽ khi bên trái là mép vực)
            if draw_left:
                left_pts = [p0, p3, (p3[0], p3[1] + d), (p0[0], p0[1] + d)]
                pygame.draw.polygon(surface, left_color, left_pts)

            # Mặt hông trước: từ p3 sang p2 (chỉ vẽ khi phía trước là mép vực)
            if draw_front:
                front_pts = [p3, p2, (p2[0], p2[1] + d), (p3[0], p3[1] + d)]
                pygame.draw.polygon(surface, front_color, front_pts)

        # Mặt nóc ô sàn
        top_pts = [p0, p1, p2, p3]
        pygame.draw.polygon(surface, top_color, top_pts)

        if draw_border:
            pygame.draw.polygon(surface, COLOR_TILE_BORDER, top_pts, 1)

    def render_board(
        self,
        map_data: MapData,
        bridge_state: Tuple[bool, ...],
        origin_x: int,
        origin_y: int,
        tile_offsets: Optional[dict] = None,
        hidden_tiles: Optional[set] = None,
        max_depth: Optional[float] = None,
        min_depth: Optional[float] = None
    ):
        """
        Vẽ toàn bộ bản đồ theo thứ tự độ sâu từ xa tới gần.
        Hỗ trợ lọc min_depth và max_depth để các ô sàn phía trước có thể che khuất nhân vật khi rơi.
        2 ô gạch chạm nhau được render phẳng liền lạc không bị bóng gờ ngăn cách.
        """
        rows, cols = map_data.rows, map_data.cols

        def has_active_tile(tr: int, tc: int) -> bool:
            """Kiểm tra xem tại (tr, tc) có ô sàn hợp lệ đang hiển thị hay không."""
            if not (0 <= tr < rows and 0 <= tc < cols):
                return False
            if hidden_tiles and (tr, tc) in hidden_tiles:
                return False
            if (tr, tc) in map_data.bridge_indices:
                idx = map_data.bridge_indices[(tr, tc)]
                return bool(bridge_state[idx])
            val = map_data.board[tr][tc]
            return val != 0 and val != 9  # Ô 9 là lỗ đích, không có mặt sàn

        # Thu thập các ô sàn cần vẽ
        all_cells = []
        for r in range(rows):
            for c in range(cols):
                if hidden_tiles and (r, c) in hidden_tiles:
                    continue
                is_bridge = (r, c) in map_data.bridge_indices
                tile_val = map_data.board[r][c]
                if tile_val != 0 or is_bridge:
                    depth = self.calc_depth(r, c)
                    all_cells.append((r, c, tile_val, is_bridge, depth))

        # Sort theo depth: r nhỏ ở xa vẽ trước, r lớn ở gần vẽ sau
        all_cells.sort(key=lambda item: item[4])

        for r, c, tile_val, is_bridge, depth in all_cells:
            # Lọc theo khoảng depth nếu có yêu cầu (phục vụ che khuất khi rơi)
            if max_depth is not None and depth > max_depth:
                continue
            if min_depth is not None and depth <= min_depth:
                continue

            z_off = 0
            if tile_offsets and (r, c) in tile_offsets:
                z_off = int(tile_offsets[(r, c)])

            # Xác định xem ô (r, c) có cần vẽ mặt hông trái và mặt hông trước hay không
            draw_left = not has_active_tile(r, c - 1)
            draw_front = not has_active_tile(r + 1, c)

            # Nếu đang có animation sàn rơi (tile_offsets) và ô lân cận rơi sâu hơn ô hiện tại
            if tile_offsets:
                z_left = int(tile_offsets.get((r, c - 1), 0))
                z_front = int(tile_offsets.get((r + 1, c), 0))
                if z_left > z_off + 2:
                    draw_left = True
                if z_front > z_off + 2:
                    draw_front = True

            if is_bridge:
                idx = map_data.bridge_indices[(r, c)]
                is_open = bridge_state[idx]
                if is_open:
                    self.draw_iso_tile(
                        self.screen, r, c, origin_x, origin_y,
                        COLOR_BRIDGE_OPEN_TOP, COLOR_BRIDGE_OPEN_LEFT, COLOR_BRIDGE_OPEN_FRONT,
                        z_offset_px=z_off,
                        draw_left=draw_left,
                        draw_front=draw_front
                    )
                else:
                    # Cầu đóng: vẽ viền mờ rỗng
                    p0 = self.grid_to_iso(r, c, origin_x, origin_y)
                    p1 = self.grid_to_iso(r, c + 1, origin_x, origin_y)
                    p2 = self.grid_to_iso(r + 1, c + 1, origin_x, origin_y)
                    p3 = self.grid_to_iso(r + 1, c, origin_x, origin_y)
                    if z_off != 0:
                        p0 = (p0[0], p0[1] + z_off)
                        p1 = (p1[0], p1[1] + z_off)
                        p2 = (p2[0], p2[1] + z_off)
                        p3 = (p3[0], p3[1] + z_off)
                    pygame.draw.polygon(self.screen, COLOR_BRIDGE_CLOSED_OUTLINE, [p0, p1, p2, p3], 1)
                continue

            if tile_val == 1:
                # Ô bình thường
                self.draw_iso_tile(
                    self.screen, r, c, origin_x, origin_y,
                    COLOR_TILE_TOP, COLOR_TILE_LEFT, COLOR_TILE_FRONT,
                    z_offset_px=z_off,
                    draw_left=draw_left,
                    draw_front=draw_front
                )

            elif tile_val == 2:
                # Ô cam dễ vỡ (Fragile)
                self.draw_iso_tile(
                    self.screen, r, c, origin_x, origin_y,
                    COLOR_FRAGILE_TOP, COLOR_FRAGILE_LEFT, COLOR_FRAGILE_FRONT,
                    z_offset_px=z_off,
                    draw_left=draw_left,
                    draw_front=draw_front
                )
                # Viền kẻ nứt biểu tượng ô vỡ
                p0 = self.grid_to_iso(r, c, origin_x, origin_y)
                p2 = self.grid_to_iso(r + 1, c + 1, origin_x, origin_y)
                if z_off != 0:
                    p0 = (p0[0], p0[1] + z_off)
                    p2 = (p2[0], p2[1] + z_off)
                pygame.draw.line(self.screen, (255, 175, 110), p0, p2, 1)

            elif tile_val == 9:
                # Lỗ đích (Goal Hole sâu thẳm theo chuẩn game gốc)
                p0 = self.grid_to_iso(r, c, origin_x, origin_y)
                p1 = self.grid_to_iso(r, c + 1, origin_x, origin_y)
                p2 = self.grid_to_iso(r + 1, c + 1, origin_x, origin_y)
                p3 = self.grid_to_iso(r + 1, c, origin_x, origin_y)
                if z_off != 0:
                    p0 = (p0[0], p0[1] + z_off)
                    p1 = (p1[0], p1[1] + z_off)
                    p2 = (p2[0], p2[1] + z_off)
                    p3 = (p3[0], p3[1] + z_off)

                # 1. Toàn bộ miệng lỗ là lòng hố sâu thẳm tối màu
                hole_face = [p0, p1, p2, p3]
                pygame.draw.polygon(self.screen, COLOR_GOAL_CORE, hole_face)

                d = self.tile_d
                if d > 0:
                    # 2. Vách sau bên trong thành hố: từ p0 sang p1 hạ xuống d (độ dày sàn)
                    b0 = (p0[0], p0[1] + d)
                    b1 = (p1[0], p1[1] + d)
                    pygame.draw.polygon(self.screen, (115, 125, 135), [p0, p1, b1, b0])

                    # 3. Vách phải bên trong thành hố: từ p1 sang p2 hạ xuống d (độ dày sàn)
                    b2 = (p2[0], p2[1] + d)
                    pygame.draw.polygon(self.screen, (90, 100, 110), [p1, p2, b2, b1])

                # 4. Viền miệng lỗ đích
                pygame.draw.polygon(self.screen, COLOR_TILE_BORDER, hole_face, 1)

            elif tile_val in (3, 4, 5, 6, 7, 8):
                # Công tắc
                self.draw_iso_tile(
                    self.screen, r, c, origin_x, origin_y,
                    COLOR_TILE_TOP, COLOR_TILE_LEFT, COLOR_TILE_FRONT,
                    z_offset_px=z_off,
                    draw_left=draw_left,
                    draw_front=draw_front
                )
                self._render_switch_icon(r, c, origin_x, origin_y, tile_val, z_off)

    def _render_switch_icon(self, r: int, c: int, origin_x: int, origin_y: int, tile_val: int, z_off: int = 0):
        """Vẽ biểu tượng công tắc trên mặt sàn hình bình hành."""
        p0 = self.grid_to_iso(r, c, origin_x, origin_y)
        p1 = self.grid_to_iso(r, c + 1, origin_x, origin_y)
        p2 = self.grid_to_iso(r + 1, c + 1, origin_x, origin_y)
        p3 = self.grid_to_iso(r + 1, c, origin_x, origin_y)

        cx = int((p0[0] + p1[0] + p2[0] + p3[0]) / 4.0)
        cy = int((p0[1] + p1[1] + p2[1] + p3[1]) / 4.0) + z_off

        if tile_val in (4, 5, 6):
            circle_color = (60, 150, 255) if tile_val == 5 else ((240, 70, 70) if tile_val == 4 else (60, 220, 120))
            rad = max(4, int(self.scale * 0.12))
            pygame.draw.circle(self.screen, (30, 40, 60), (cx, cy), rad + 2)
            pygame.draw.circle(self.screen, circle_color, (cx, cy), rad)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), max(2, rad // 2))

        elif tile_val in (3, 8):
            x_color = (190, 40, 40) if tile_val == 3 else (40, 180, 80)
            txt = self.font_bold.render("X", True, x_color)
            rect = txt.get_rect(center=(cx, cy - 1))
            self.screen.blit(txt, rect)

        elif tile_val == 7:
            txt = self.font_bold.render("( )", True, (160, 60, 230))
            rect = txt.get_rect(center=(cx, cy - 1))
            self.screen.blit(txt, rect)

    def _draw_cuboid_bounds(
        self,
        rmin: float, rmax: float,
        cmin: float, cmax: float,
        zmin: float, zmax: float,
        origin_x: int, origin_y: int,
        top_color: Tuple[int, int, int],
        left_color: Tuple[int, int, int],
        front_color: Tuple[int, int, int],
        draw_shadow: bool = True
    ):
        """Vẽ hình hộp chữ nhật 3D với bóng đổ mờ nhẹ (soft blurred shadow)."""
        def p(r, c, z):
            return self.grid_to_iso(r, c, origin_x, origin_y, z)

        # 8 đỉnh
        b0 = p(rmin, cmin, zmin)
        b1 = p(rmin, cmax, zmin)
        b2 = p(rmax, cmax, zmin)
        b3 = p(rmax, cmin, zmin)

        t0 = p(rmin, cmin, zmax)
        t1 = p(rmin, cmax, zmax)
        t2 = p(rmax, cmax, zmax)
        t3 = p(rmax, cmin, zmax)

        # 1. Bóng đổ mờ nhẹ (Soft Blurred Shadow) phía sau bên phải
        if draw_shadow and zmin >= 0:
            s_pts = [
                p(rmin + 0.05, cmin + 0.25, 0),
                p(rmin - 0.45, cmax + 0.75, 0),
                p(rmax - 0.10, cmax + 0.75, 0),
                p(rmax + 0.10, cmin + 0.25, 0)
            ]
            # Alpha mờ dần nếu khối ở trên cao
            alpha = max(20, int(90 - zmin * 18))
            draw_soft_shadow(self.screen, s_pts, base_alpha=alpha)

        # Mặt trái: b0 -> b3 -> t3 -> t0
        pygame.draw.polygon(self.screen, left_color, [b0, b3, t3, t0])

        # Mặt trước: b3 -> b2 -> t2 -> t3
        pygame.draw.polygon(self.screen, front_color, [b3, b2, t2, t3])

        # Mặt nóc: t0 -> t1 -> t2 -> t3
        top_face = [t0, t1, t2, t3]
        pygame.draw.polygon(self.screen, top_color, top_face)

        # Viền nổi bật cạnh sắc nét
        pygame.draw.lines(self.screen, COLOR_BLOCK_EDGE, True, top_face, 1)
        pygame.draw.line(self.screen, COLOR_BLOCK_EDGE, t3, b3, 1)
        pygame.draw.line(self.screen, COLOR_BLOCK_EDGE, t2, b2, 1)

    def render_block(
        self,
        block: BlockState,
        origin_x: int,
        origin_y: int,
        pulse_val: float = 0.0,
        z_offset: float = 0.0
    ):
        """
        Vẽ khối Bloxorz (standing, horizontal, vertical, split) theo đúng hệ trục 3D mới.
        """
        ori = block.orientation

        if ori == Orientation.STANDING:
            self._draw_cuboid_bounds(
                block.r, block.r + 1,
                block.c, block.c + 1,
                z_offset, z_offset + 2.0,
                origin_x, origin_y,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_FRONT
            )

        elif ori == Orientation.HORIZONTAL:
            self._draw_cuboid_bounds(
                block.r, block.r + 1,
                block.c, block.c + 2,
                z_offset, z_offset + 1.0,
                origin_x, origin_y,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_FRONT
            )

        elif ori == Orientation.VERTICAL:
            self._draw_cuboid_bounds(
                block.r, block.r + 2,
                block.c, block.c + 1,
                z_offset, z_offset + 1.0,
                origin_x, origin_y,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_FRONT
            )

        elif ori == Orientation.SPLIT:
            cubes = [(block.r, block.c, 0), (block.r1, block.c1, 1)]
            cubes.sort(key=lambda item: item[0] * 100 + item[1])

            for r, c, idx in cubes:
                is_active = (block.active_cube == idx)
                top_col = COLOR_CUBE0_TOP if idx == 0 else COLOR_CUBE1_TOP
                left_col = COLOR_CUBE0_LEFT if idx == 0 else COLOR_CUBE1_LEFT
                front_col = COLOR_CUBE0_FRONT if idx == 0 else COLOR_CUBE1_FRONT

                self._draw_cuboid_bounds(
                    r, r + 1,
                    c, c + 1,
                    z_offset, z_offset + 1.0,
                    origin_x, origin_y,
                    top_col, left_col, front_col
                )

                if is_active:
                    p_mid = self.grid_to_iso(r + 0.5, c + 0.5, origin_x, origin_y, z=1.0)
                    rad = int(self.scale * 0.45 + math.sin(pulse_val * 4.0) * 3)
                    pygame.draw.circle(self.screen, (255, 235, 100), p_mid, rad, 2)
