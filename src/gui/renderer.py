"""
Module: renderer.py
Mô tả: Bộ dựng hình đồ họa 3D Isometric cho game Bloxorz bằng Pygame.
      - Chiếu lưới ma trận (row, col) thành không gian 3D Isometric có chiều sâu, độ dày và bóng đổ.
      - Vẽ các loại ô sàn đặc trưng: ô thường, ô cam dễ vỡ (Fragile), cầu đóng/mở (Bridge),
        lỗ đích phát sáng (Goal), và các loại công tắc (Tròn mềm, Chữ X nặng, Phân thân).
      - Vẽ khối hộp Bloxorz 1x1x2 đa chiều (đứng cao 2 tầng, nằm ngang, nằm dọc, phân thân 2 khối 1x1x1)
        với hiệu ứng đổ bóng, đánh sáng các mặt và viền bóng bẩy.
"""

import pygame
import math
from typing import Tuple, List, Optional
from src.core.block import BlockState, Orientation
from src.core.map_loader import MapData


# Bảng màu thẩm mỹ cao (Curated Modern Palette)
COLOR_BG_GRADIENT_TOP = (15, 20, 32)
COLOR_BG_GRADIENT_BOTTOM = (24, 30, 48)

COLOR_TILE_TOP = (210, 218, 226)
COLOR_TILE_LEFT = (160, 170, 185)
COLOR_TILE_RIGHT = (130, 140, 155)
COLOR_TILE_BORDER = (100, 110, 125)

COLOR_FRAGILE_TOP = (245, 120, 45)
COLOR_FRAGILE_LEFT = (210, 90, 25)
COLOR_FRAGILE_RIGHT = (175, 70, 15)

COLOR_BRIDGE_OPEN_TOP = (235, 180, 60)
COLOR_BRIDGE_OPEN_LEFT = (195, 145, 40)
COLOR_BRIDGE_OPEN_RIGHT = (160, 115, 25)

COLOR_BRIDGE_CLOSED_OUTLINE = (55, 65, 85)

COLOR_GOAL_HALO = (255, 220, 50, 70)
COLOR_GOAL_CORE = (18, 20, 28)
COLOR_GOAL_BORDER = (255, 200, 40)

# Màu của khối Bloxorz
COLOR_BLOCK_TOP = (225, 135, 65)
COLOR_BLOCK_LEFT = (150, 75, 30)
COLOR_BLOCK_RIGHT = (185, 100, 45)
COLOR_BLOCK_EDGE = (255, 175, 115)

COLOR_SHADOW = (10, 12, 18, 90)

# Khối phân thân
COLOR_CUBE0_TOP = (70, 190, 245)
COLOR_CUBE0_LEFT = (40, 140, 195)
COLOR_CUBE0_RIGHT = (55, 165, 220)

COLOR_CUBE1_TOP = (215, 105, 245)
COLOR_CUBE1_LEFT = (165, 65, 195)
COLOR_CUBE1_RIGHT = (190, 85, 220)


from src.gui.safe_font import get_safe_font, SafeFont


class IsoRenderer:
    """
    Trình dựng hình đồ họa 3D Isometric.
    """

    def __init__(self, screen, tile_width: int = 44, tile_height: int = 22, tile_depth: int = 8):
        self.screen = screen
        self.tile_w = tile_width
        self.tile_h = tile_height
        self.tile_d = tile_depth
        self.block_unit_h = 28  # Chiều cao của 1 tầng khối 1x1x1

        # Khởi tạo font chữ để vẽ ký hiệu công tắc an toàn
        self.font_small = get_safe_font("segoeui", 13, bold=True)
        self.font_bold = get_safe_font("segoeui", 15, bold=True)

    def grid_to_iso(self, r: int, c: int, origin_x: int, origin_y: int) -> Tuple[int, int]:
        """
        Chuyển đổi tọa độ ma trận (row, col) sang tọa độ màn hình Isometric (x, y).
        """
        iso_x = origin_x + int((c - r) * (self.tile_w / 2.0))
        iso_y = origin_y + int((c + r) * (self.tile_h / 2.0))
        return (iso_x, iso_y)

    def draw_iso_tile(
        self,
        surface: pygame.Surface,
        cx: int,
        cy: int,
        top_color: Tuple[int, int, int],
        left_color: Tuple[int, int, int],
        right_color: Tuple[int, int, int],
        depth: Optional[int] = None,
        draw_border: bool = True
    ):
        """
        Vẽ một ô sàn hình quả trám có độ dày (3D Isometric tile).
        """
        d = self.tile_d if depth is None else depth
        hw = self.tile_w // 2
        hh = self.tile_h // 2

        # 4 đỉnh của mặt trên ô sàn
        top_pts = [
            (cx, cy - hh),       # Đỉnh trên
            (cx + hw, cy),       # Đỉnh phải
            (cx, cy + hh),       # Đỉnh dưới
            (cx - hw, cy)        # Đỉnh trái
        ]

        if d > 0:
            # Mặt hông trái
            left_pts = [
                (cx - hw, cy),
                (cx, cy + hh),
                (cx, cy + hh + d),
                (cx - hw, cy + d)
            ]
            pygame.draw.polygon(surface, left_color, left_pts)

            # Mặt hông phải
            right_pts = [
                (cx, cy + hh),
                (cx + hw, cy),
                (cx + hw, cy + d),
                (cx, cy + hh + d)
            ]
            pygame.draw.polygon(surface, right_color, right_pts)

        # Mặt trên
        pygame.draw.polygon(surface, top_color, top_pts)

        if draw_border:
            pygame.draw.polygon(surface, COLOR_TILE_BORDER, top_pts, 1)

    def render_board(
        self,
        map_data: MapData,
        bridge_state: Tuple[bool, ...],
        origin_x: int,
        origin_y: int
    ):
        """
        Vẽ toàn bộ bản đồ sàn đấu theo thứ tự từ xa lại gần (hàng + cột tăng dần).
        """
        rows, cols = map_data.rows, map_data.cols

        # Duyệt theo đường chéo d = r + c để bảo đảm tính đúng của Painter's Algorithm
        for diag in range(rows + cols - 1):
            for r in range(rows):
                c = diag - r
                if not (0 <= c < cols):
                    continue

                cx, cy = self.grid_to_iso(r, c, origin_x, origin_y)

                # Kiểm tra nếu là ô cầu
                if (r, c) in map_data.bridge_indices:
                    idx = map_data.bridge_indices[(r, c)]
                    is_open = bridge_state[idx]
                    if is_open:
                        # Cầu đang mở: hiện ô sàn màu đồng đặc biệt
                        self.draw_iso_tile(
                            self.screen, cx, cy,
                            COLOR_BRIDGE_OPEN_TOP,
                            COLOR_BRIDGE_OPEN_LEFT,
                            COLOR_BRIDGE_OPEN_RIGHT
                        )
                    else:
                        # Cầu đang đóng: vẽ khung đứt mờ ảo mô tả khoảng trống vực sâu
                        hw = self.tile_w // 2
                        hh = self.tile_h // 2
                        outline_pts = [
                            (cx, cy - hh), (cx + hw, cy),
                            (cx, cy + hh), (cx - hw, cy)
                        ]
                        pygame.draw.polygon(self.screen, COLOR_BRIDGE_CLOSED_OUTLINE, outline_pts, 1)
                    continue

                tile_val = map_data.board[r][c]
                if tile_val == 0:
                    continue  # Vực thẳm / Hư vô

                # Ô thông thường hoặc ô đặc biệt
                if tile_val == 1:
                    self.draw_iso_tile(self.screen, cx, cy, COLOR_TILE_TOP, COLOR_TILE_LEFT, COLOR_TILE_RIGHT)

                elif tile_val == 2:
                    # Ô cam dễ vỡ (Fragile)
                    self.draw_iso_tile(self.screen, cx, cy, COLOR_FRAGILE_TOP, COLOR_FRAGILE_LEFT, COLOR_FRAGILE_RIGHT)
                    # Vẽ vân lưới mỏng biểu thị ô có thể nứt vỡ
                    hw = self.tile_w // 2
                    hh = self.tile_h // 2
                    pygame.draw.line(self.screen, (255, 170, 110), (cx - hw // 2, cy), (cx + hw // 2, cy), 1)

                elif tile_val == 9:
                    # Lỗ đích (Goal Hole)
                    self.draw_iso_tile(self.screen, cx, cy, (40, 45, 60), (25, 30, 40), (20, 25, 35))
                    # Lõi lỗ sâu hút phát sáng vàng
                    pygame.draw.circle(self.screen, COLOR_GOAL_CORE, (cx, cy), self.tile_h // 2 - 2)
                    pygame.draw.circle(self.screen, COLOR_GOAL_BORDER, (cx, cy), self.tile_h // 2 - 2, 2)
                    # Vành hào quang
                    pygame.draw.circle(self.screen, (255, 235, 100), (cx, cy), self.tile_h // 4)

                elif tile_val in (3, 4, 5, 6, 7, 8):
                    # Ô chứa công tắc: vẽ sàn trước rồi vẽ biểu tượng công tắc lên trên
                    self.draw_iso_tile(self.screen, cx, cy, COLOR_TILE_TOP, COLOR_TILE_LEFT, COLOR_TILE_RIGHT)
                    self._render_switch_icon(cx, cy, tile_val)

    def _render_switch_icon(self, cx: int, cy: int, tile_val: int):
        """Vẽ biểu tượng từng loại công tắc trên mặt ô sàn."""
        if tile_val in (4, 5, 6):
            # Công tắc nhẹ (tròn): vòng tròn nổi màu xanh/cam
            circle_color = (60, 150, 255) if tile_val == 5 else ((240, 70, 70) if tile_val == 4 else (60, 220, 120))
            pygame.draw.circle(self.screen, (30, 40, 60), (cx, cy), 8)
            pygame.draw.circle(self.screen, circle_color, (cx, cy), 6)
            pygame.draw.circle(self.screen, (255, 255, 255), (cx, cy), 3)

        elif tile_val in (3, 8):
            # Công tắc nặng (Chữ X): biểu tượng X đậm nét
            x_color = (190, 40, 40) if tile_val == 3 else (40, 180, 80)
            txt = self.font_bold.render("X", True, x_color)
            rect = txt.get_rect(center=(cx, cy - 1))
            self.screen.blit(txt, rect)

        elif tile_val == 7:
            # Công tắc phân thân (Split switch): biểu tượng ( )
            txt = self.font_bold.render("( )", True, (160, 60, 230))
            rect = txt.get_rect(center=(cx, cy - 1))
            self.screen.blit(txt, rect)

    def render_block(
        self,
        block: BlockState,
        origin_x: int,
        origin_y: int,
        pulse_val: float = 0.0
    ):
        """
        Vẽ khối Bloxorz 1x1x2 hoặc 2 khối phân thân 1x1x1 theo tọa độ và hướng hiện tại.
        """
        ori = block.orientation

        if ori == Orientation.STANDING:
            cx, cy = self.grid_to_iso(block.r, block.c, origin_x, origin_y)
            # Khối đứng cao gấp 2 lần đơn vị khối (2 * block_unit_h)
            height = self.block_unit_h * 2
            self._draw_3d_box(
                cx, cy,
                self.tile_w, self.tile_h, height,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_RIGHT
            )

        elif ori == Orientation.HORIZONTAL:
            # Chiếm (r, c) và (r, c + 1): vùng chân rộng 1 hàng x 2 cột, cao 1 đơn vị
            self._draw_cuboid(
                block.r, block.c, block.r, block.c + 1, self.block_unit_h,
                origin_x, origin_y,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_RIGHT
            )

        elif ori == Orientation.VERTICAL:
            # Chiếm (r, c) và (r + 1, c): vùng chân rộng 2 hàng x 1 cột, cao 1 đơn vị
            self._draw_cuboid(
                block.r, block.c, block.r + 1, block.c, self.block_unit_h,
                origin_x, origin_y,
                COLOR_BLOCK_TOP, COLOR_BLOCK_LEFT, COLOR_BLOCK_RIGHT
            )

        elif ori == Orientation.SPLIT:
            # Hai khối lập phương 1x1x1 độc lập
            # Vẽ khối ở xa trước để không bị che khuất sai
            cubes = [(block.r, block.c, 0), (block.r1, block.c1, 1)]
            cubes.sort(key=lambda item: item[0] + item[1])

            for r, c, idx in cubes:
                cx, cy = self.grid_to_iso(r, c, origin_x, origin_y)
                is_active = (block.active_cube == idx)
                top_col = COLOR_CUBE0_TOP if idx == 0 else COLOR_CUBE1_TOP
                left_col = COLOR_CUBE0_LEFT if idx == 0 else COLOR_CUBE1_LEFT
                right_col = COLOR_CUBE0_RIGHT if idx == 0 else COLOR_CUBE1_RIGHT

                self._draw_3d_box(
                    cx, cy,
                    self.tile_w, self.tile_h, self.block_unit_h,
                    top_col, left_col, right_col
                )

                # Vòng sáng xung quanh khối đang được chọn điều khiển (Active cube)
                if is_active:
                    halo_r = int(self.tile_w // 2 + 3 + math.sin(pulse_val * 4.0) * 2)
                    pygame.draw.ellipse(
                        self.screen,
                        (255, 235, 100),
                        (cx - halo_r, cy - halo_r // 2 - self.block_unit_h, halo_r * 2, halo_r),
                        2
                    )

    def _draw_3d_box(
        self,
        cx: int,
        cy: int,
        w: int,
        h: int,
        height: int,
        top_color: Tuple[int, int, int],
        left_color: Tuple[int, int, int],
        right_color: Tuple[int, int, int]
    ):
        """Vẽ một hình hộp chữ nhật Isometric 3D đứng trên ô tâm (cx, cy)."""
        hw = w // 2
        hh = h // 2

        # Đáy (chân khối trên mặt sàn)
        b_top = (cx, cy - hh)
        b_right = (cx + hw, cy)
        b_bottom = (cx, cy + hh)
        b_left = (cx - hw, cy)

        # Đỉnh trên (nâng cao theo trục y âm một đoạn = height)
        t_top = (cx, cy - hh - height)
        t_right = (cx + hw, cy - height)
        t_bottom = (cx, cy + hh - height)
        t_left = (cx - hw, cy - height)

        # Mặt trái (Left face)
        left_pts = [b_left, b_bottom, t_bottom, t_left]
        pygame.draw.polygon(self.screen, left_color, left_pts)

        # Mặt phải (Right face)
        right_pts = [b_bottom, b_right, t_right, t_bottom]
        pygame.draw.polygon(self.screen, right_color, right_pts)

        # Mặt nóc (Top face)
        top_pts = [t_top, t_right, t_bottom, t_left]
        pygame.draw.polygon(self.screen, top_color, top_pts)

        # Đường viền viền sáng trên các cạnh
        pygame.draw.lines(self.screen, COLOR_BLOCK_EDGE, True, top_pts, 1)
        pygame.draw.line(self.screen, COLOR_BLOCK_EDGE, t_bottom, b_bottom, 1)

    def _draw_cuboid(
        self,
        r0: int, c0: int, r1: int, c1: int,
        height: int,
        origin_x: int, origin_y: int,
        top_color: Tuple[int, int, int],
        left_color: Tuple[int, int, int],
        right_color: Tuple[int, int, int]
    ):
        """
        Vẽ hình hộp isometric phủ vùng chân từ ô (r0, c0) đến ô (r1, c1) (bao gồm cả hai đầu).
        Dùng chung cho khối nằm ngang (1x2 ô) và nằm dọc (2x1 ô). Mép vùng chân nằm
        cách tâm ô 0.5 đơn vị, nên bốn đỉnh là: sau, phải, trước, trái.
        """
        def pt(rr: float, cc: float) -> Tuple[int, int]:
            x = origin_x + (cc - rr) * (self.tile_w / 2.0)
            y = origin_y + (cc + rr) * (self.tile_h / 2.0)
            return (int(x), int(y))

        rmin, rmax = r0 - 0.5, r1 + 0.5
        cmin, cmax = c0 - 0.5, c1 + 0.5

        back = pt(rmin, cmin)
        right = pt(rmin, cmax)
        front = pt(rmax, cmax)
        left = pt(rmax, cmin)

        def up(p):
            return (p[0], p[1] - height)

        # Mặt trái: nối đỉnh trái -> đỉnh trước
        pygame.draw.polygon(self.screen, left_color, [left, front, up(front), up(left)])
        # Mặt phải: nối đỉnh trước -> đỉnh phải
        pygame.draw.polygon(self.screen, right_color, [front, right, up(right), up(front)])
        # Mặt nóc
        top_pts = [up(back), up(right), up(front), up(left)]
        pygame.draw.polygon(self.screen, top_color, top_pts)
        pygame.draw.lines(self.screen, COLOR_BLOCK_EDGE, True, top_pts, 1)
        pygame.draw.line(self.screen, COLOR_BLOCK_EDGE, up(front), front, 1)
