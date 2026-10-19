"""
Module: board_animator.py
Mô tả: Quản lý và xử lý hoạt ảnh tái lập màn chơi (Board Restart Animation Sequence):
      1. PHASE_FALL: Các ô gạch lần lượt rơi ngẫu nhiên xuống vực (1-2s).
      2. PHASE_WAIT: Màn hình chờ khởi động lại màn chơi với hiệu ứng loading.
      3. PHASE_RISE: Các ô gạch từ dưới bay vút lên lắp lại sàn nguyên vẹn.
      4. PHASE_FLASH: Màn hình chớp nháy 1 nhịp báo hiệu hoàn thành.
      5. PHASE_SPAWN: Nhân vật Bloxorz đáp xuống vị trí bắt đầu và sẵn sàng chơi.
"""

import random
import pygame
from typing import Dict, Tuple, Set, Optional, Callable, List
from src.core.map_loader import MapData
from src.gui.safe_font import get_safe_font


class BoardRestartAnimator:
    """Bộ điều phối chuỗi hoạt ảnh tái lập không gian bản đồ khi thua hoặc khởi động lại."""

    PHASE_IDLE = 0
    PHASE_FALL = 1
    PHASE_WAIT = 2
    PHASE_RISE = 3
    PHASE_FLASH = 4
    PHASE_SPAWN = 5

    def __init__(self):
        self.phase = self.PHASE_IDLE
        self.elapsed = 0.0
        self.on_complete: Optional[Callable[[], None]] = None
        self.map_data: Optional[MapData] = None

        self.fall_delays: Dict[Tuple[int, int], float] = {}
        self.rise_delays: Dict[Tuple[int, int], float] = {}
        self.tile_offsets: Dict[Tuple[int, int], float] = {}
        self.hidden_tiles: Set[Tuple[int, int]] = set()

        # Cấu hình thời lượng từng giai đoạn (Tổng cộng ~3.8 giây hoàn mỹ)
        self.fall_duration = 1.35     # Các ô lần lượt rơi trong khoảng 1.35s (khoảng 1-2s)
        self.wait_duration = 0.65     # Màn hình chờ 0.65s
        self.rise_duration = 1.35     # Các ô từ dưới bay lên trong khoảng 1.35s
        self.flash_duration = 0.25    # Chớp nháy 1 nhịp 0.25s
        self.spawn_duration = 0.35    # Nhân vật đáp xuống trong 0.35s

        self.tile_action_duration = 0.55  # Thời gian rơi/bay của từng ô đơn lẻ
        self.drop_distance = 800.0        # Độ sâu rơi tụt khỏi màn hình

        # Font giao diện màn hình chờ
        self.font_badge = get_safe_font("segoeui", 12, bold=True)
        self.font_title = get_safe_font("segoeui", 22, bold=True)
        self.font_sub = get_safe_font("segoeui", 14)
        self.font_hint = get_safe_font("segoeui", 11)

    def is_animating(self) -> bool:
        """Kiểm tra xem hoạt ảnh tái lập màn chơi có đang chạy hay không."""
        return self.phase != self.PHASE_IDLE

    def start(self, map_data: MapData, on_complete: Optional[Callable[[], None]] = None):
        """Kích hoạt chuỗi hoạt ảnh tái lập màn chơi."""
        self.map_data = map_data
        self.on_complete = on_complete
        self.phase = self.PHASE_FALL
        self.elapsed = 0.0
        self.tile_offsets.clear()
        self.hidden_tiles.clear()

        # Thu thập danh sách tất cả các ô hiện hữu trên sàn
        all_tiles: List[Tuple[int, int]] = []
        for r in range(map_data.rows):
            for c in range(map_data.cols):
                if map_data.board[r][c] != 0 or (r, c) in map_data.bridge_indices:
                    all_tiles.append((r, c))

        # Gán độ trễ ngẫu nhiên cho từng ô khi rơi
        max_delay = max(0.1, self.fall_duration - self.tile_action_duration)
        self.fall_delays = {tile: random.uniform(0.0, max_delay) for tile in all_tiles}

        # Gán độ trễ ngẫu nhiên cho từng ô khi bay lên lại
        max_rise_delay = max(0.1, self.rise_duration - self.tile_action_duration)
        self.rise_delays = {tile: random.uniform(0.0, max_rise_delay) for tile in all_tiles}

    def update(self, dt: float):
        """Cập nhật tiến trình qua từng khung hình (Frame Update)."""
        if self.phase == self.PHASE_IDLE:
            return

        self.elapsed += dt

        if self.phase == self.PHASE_FALL:
            self._update_fall()
        elif self.phase == self.PHASE_WAIT:
            self._update_wait()
        elif self.phase == self.PHASE_RISE:
            self._update_rise()
        elif self.phase == self.PHASE_FLASH:
            self._update_flash()
        elif self.phase == self.PHASE_SPAWN:
            self._update_spawn()

    def _update_fall(self):
        """Giai đoạn 1: Các ô lần lượt rơi ngẫu nhiên xuống vực."""
        self.tile_offsets.clear()
        self.hidden_tiles.clear()

        all_fallen = True
        for tile, delay in self.fall_delays.items():
            if self.elapsed < delay:
                all_fallen = False
                self.tile_offsets[tile] = 0.0
            else:
                t = (self.elapsed - delay) / self.tile_action_duration
                if t >= 1.0:
                    self.hidden_tiles.add(tile)
                    self.tile_offsets[tile] = self.drop_distance
                else:
                    all_fallen = False
                    # Rơi nhanh dần theo gia tốc trọng lực
                    self.tile_offsets[tile] = self.drop_distance * (t ** 2.2)

        if self.elapsed >= self.fall_duration or all_fallen:
            self.phase = self.PHASE_WAIT
            self.elapsed = 0.0
            self.hidden_tiles = set(self.fall_delays.keys())

    def _update_wait(self):
        """Giai đoạn 2: Bàn cờ trống không, hiện màn hình chờ khởi động lại."""
        self.hidden_tiles = set(self.fall_delays.keys())
        if self.elapsed >= self.wait_duration:
            self.phase = self.PHASE_RISE
            self.elapsed = 0.0
            self.hidden_tiles = set(self.fall_delays.keys())

    def _update_rise(self):
        """Giai đoạn 3: Các ô từ dưới đáy vực vút bay lên lắp lại sàn."""
        self.tile_offsets.clear()
        self.hidden_tiles.clear()

        all_docked = True
        for tile, delay in self.rise_delays.items():
            if self.elapsed < delay:
                all_docked = False
                self.hidden_tiles.add(tile)
                self.tile_offsets[tile] = self.drop_distance
            else:
                t = min(1.0, (self.elapsed - delay) / self.tile_action_duration)
                if t >= 1.0:
                    self.tile_offsets[tile] = 0.0
                else:
                    all_docked = False
                    inv = 1.0 - t
                    # Giảm tốc mượt mà (Ease-out) khi tiếp đất
                    self.tile_offsets[tile] = self.drop_distance * (inv ** 2.5)

        if self.elapsed >= self.rise_duration or all_docked:
            self.phase = self.PHASE_FLASH
            self.elapsed = 0.0
            self.tile_offsets.clear()
            self.hidden_tiles.clear()

    def _update_flash(self):
        """Giai đoạn 4: Chớp nháy 1 nhịp khi toàn bộ sàn đã lắp ráp xong."""
        if self.elapsed >= self.flash_duration:
            self.phase = self.PHASE_SPAWN
            self.elapsed = 0.0

    def _update_spawn(self):
        """Giai đoạn 5: Nhân vật rơi từ trên cao đáp xuống vị trí bắt đầu."""
        if self.elapsed >= self.spawn_duration:
            self.skip_to_end()

    def get_spawn_z_offset(self) -> float:
        """Độ cao Z của nhân vật khi đang rơi tiếp đất ở giai đoạn SPAWN."""
        if self.phase == self.PHASE_SPAWN:
            p = min(1.0, self.elapsed / self.spawn_duration)
            inv = 1.0 - p
            return 5.0 * (inv ** 2)
        return 0.0

    def should_render_block(self) -> bool:
        """Chỉ cho phép vẽ nhân vật ở giai đoạn SPAWN."""
        return self.phase == self.PHASE_SPAWN

    def skip_to_end(self):
        """Bỏ qua nhanh và kết thúc ngay hoạt ảnh."""
        callback = self.on_complete
        self.reset()
        if callback:
            callback()

    def reset(self):
        """Đặt lại animator về trạng thái rảnh rỗi."""
        self.phase = self.PHASE_IDLE
        self.elapsed = 0.0
        self.tile_offsets.clear()
        self.hidden_tiles.clear()
        self.on_complete = None
        self.map_data = None

    def render_overlay(self, screen: pygame.Surface, board_width: int, screen_height: int):
        """Vẽ các lớp hiệu ứng giao diện (Màn hình chờ, Flash chớp sáng)."""
        if self.phase == self.PHASE_WAIT:
            self._render_wait_modal(screen, board_width, screen_height)
        elif self.phase == self.PHASE_FLASH:
            self._render_screen_flash(screen, board_width, screen_height)

    def _render_wait_modal(self, screen: pygame.Surface, board_width: int, screen_height: int):
        """Vẽ hộp thông báo chờ khởi động lại màn chơi."""
        # Lớp phủ mờ nền bàn cờ (0 -> board_width)
        overlay = pygame.Surface((board_width, screen_height), pygame.SRCALPHA)
        fade_alpha = int(min(195, 195 * (self.elapsed / 0.18)))
        overlay.fill((10, 14, 24, fade_alpha))
        screen.blit(overlay, (0, 0))

        # Hộp card trung tâm
        card_w, card_h = 450, 210
        card_x = (board_width - card_w) // 2
        card_y = (screen_height - card_h) // 2 - 20
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

        pygame.draw.rect(screen, (22, 28, 42), card_rect, border_radius=16)
        border_col = (88, 166, 255)  # Màu xanh cyan neon hiện đại
        pygame.draw.rect(screen, border_col, card_rect, width=2, border_radius=16)

        # 1. Badge phía trên
        badge_surf = self.font_badge.render("HỆ THỐNG ĐANG TÁI LẬP BẢN ĐỒ", True, border_col)
        badge_rect = badge_surf.get_rect(center=(card_rect.centerx, card_rect.y + 32))
        screen.blit(badge_surf, badge_rect)

        # 2. Tiêu đề
        title_surf = self.font_title.render("KHỞI ĐỘNG LẠI MÀN CHƠI...", True, (240, 245, 250))
        title_rect = title_surf.get_rect(center=(card_rect.centerx, card_rect.y + 75))
        screen.blit(title_surf, title_rect)

        # 3. Phụ đề
        sub_surf = self.font_sub.render("Các khối gạch đang được định vị lại...", True, (145, 155, 175))
        sub_rect = sub_surf.get_rect(center=(card_rect.centerx, card_rect.y + 115))
        screen.blit(sub_surf, sub_rect)

        # 4. Thanh tiến trình nạp
        bar_w, bar_h = 320, 6
        bar_x = card_rect.centerx - bar_w // 2
        bar_y = card_rect.y + 148
        pygame.draw.rect(screen, (35, 45, 65), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        progress = min(1.0, self.elapsed / self.wait_duration)
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(screen, border_col, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        # 5. Gợi ý bỏ qua nhanh
        hint_surf = self.font_hint.render("(Bấm phím bất kỳ hoặc nhấp chuột để tiếp tục ngay)", True, (120, 135, 155))
        hint_rect = hint_surf.get_rect(center=(card_rect.centerx, card_rect.y + 180))
        screen.blit(hint_surf, hint_rect)

    def _render_screen_flash(self, screen: pygame.Surface, board_width: int, screen_height: int):
        """Vẽ hiệu ứng chớp sáng 1 nhịp khi hoàn tất ghép sàn."""
        p = min(1.0, self.elapsed / self.flash_duration)
        alpha = int(210 * ((1.0 - p) ** 1.6))
        if alpha > 0:
            flash_surf = pygame.Surface((board_width, screen_height), pygame.SRCALPHA)
            flash_surf.fill((235, 245, 255, alpha))
            screen.blit(flash_surf, (0, 0))
