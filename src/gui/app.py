"""
Module: app.py
Mô tả: Ứng dụng giao diện đồ họa chính (Pygame GUI) cho game Bloxorz:
      - Tương tác chơi thủ công hoàn chỉnh (lăn khối, kích hoạt cầu, công tắc, phân thân, thắng/thua).
      - Tích hợp 4 thuật toán tìm kiếm (BFS, DFS, UCS, A*) chạy nền đa luồng (threading) mượt mà.
      - Bảng điều khiển phân tích số liệu: thời gian, bộ nhớ cực đại, số nút mở rộng, độ dài giải pháp.
      - Trình chiếu động (animation replay) từng bước đi của lời giải với tùy chỉnh tốc độ.
      - Hỗ trợ đổi qua lại giữa 33 màn chơi của game Bloxorz.
"""

import os
import sys
import glob
import time
import re
import threading
import pygame
from typing import List, Optional, Dict, Any, Tuple

from src.core.block import BlockState, Orientation, Direction
from src.core.map_loader import MapData, load_map_from_file
from src.core.game_state import GameState
from src.gui.safe_font import patch_pygame_font, get_safe_font
from src.gui.renderer import IsoRenderer
from src.gui.animator import BlockAnimator
from src.gui.board_animator import BoardRestartAnimator

# Áp dụng SafeFont để phòng ngừa triệt để lỗi segfault của pygame trên Python 3.14
patch_pygame_font()
from src.solvers import (
    SearchResult,
    solve_bfs,
    solve_dfs,
    solve_ids,
    solve_ucs,
    solve_astar
)


# Bảng màu giao diện tối (Dark Modern Theme)
BG_COLOR = (15, 18, 26)
PANEL_BG = (22, 27, 38)
PANEL_BORDER = (45, 55, 75)
TEXT_WHITE = (240, 243, 246)
TEXT_MUTED = (145, 155, 170)
TEXT_ACCENT = (88, 166, 255)
TEXT_SUCCESS = (63, 185, 80)
TEXT_DANGER = (248, 81, 73)
TEXT_WARN = (210, 153, 34)

BTN_DEFAULT = (35, 43, 60)
BTN_HOVER = (48, 58, 80)
BTN_ACTIVE = (65, 80, 110)
BTN_PRIMARY = (31, 111, 235)
BTN_PRIMARY_HOVER = (45, 128, 255)
BTN_SUCCESS = (35, 134, 54)
BTN_SUCCESS_HOVER = (46, 160, 67)


class Button:
    """Nút bấm tương tác trên giao diện."""

    def __init__(
        self,
        rect: Any,
        text: str,
        callback,
        font: Any,
        bg_color=BTN_DEFAULT,
        hover_color=BTN_HOVER,
        text_color=TEXT_WHITE,
        border_radius: int = 6
    ):
        self.rect = rect
        self.text = text
        self.callback = callback
        self.font = font
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.text_color = text_color
        self.border_radius = border_radius
        self.is_hovered = False

    def update(self, mouse_pos):
        self.is_hovered = self.rect.collidepoint(mouse_pos)

    def draw(self, surface: pygame.Surface):
        color = self.hover_color if self.is_hovered else self.bg_color
        pygame.draw.rect(surface, color, self.rect, border_radius=self.border_radius)
        pygame.draw.rect(surface, PANEL_BORDER, self.rect, width=1, border_radius=self.border_radius)

        txt_surf = self.font.render(self.text, True, self.text_color)
        txt_rect = txt_surf.get_rect(center=self.rect.center)
        surface.blit(txt_surf, txt_rect)

    def handle_event(self, event) -> bool:
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.is_hovered and self.callback:
                self.callback()
                return True
        return False


class BloxorzApp:
    """Ứng dụng chính điều phối trò chơi và trình giải thuật toán."""

    def __init__(self, levels_dir: str = "Source/levels", width: int = 1260, height: int = 780):
        pygame.init()
        pygame.display.set_caption("Bloxorz Solver")
        self.width = width
        self.height = height
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode(
            (width, height),
            pygame.DOUBLEBUF | pygame.SCALED | pygame.RESIZABLE
        )
        self.clock = pygame.time.Clock()

        # Tải danh sách các màn chơi
        self.levels_dir = levels_dir
        self.level_files = sorted(glob.glob(os.path.join(levels_dir, "*.txt")))
        if not self.level_files:
            # Dự phòng thư mục hiện tại
            self.level_files = sorted(glob.glob("levels/*.txt"))
        self.current_level_idx = 0

        # Khởi tạo Renderer & Animator
        self.renderer = IsoRenderer(self.screen)
        self.animator = BlockAnimator()
        self.board_animator = BoardRestartAnimator()

        # Khởi tạo font chữ an toàn bằng SafeFont
        self.font_title = get_safe_font("segoeui", 20, bold=True)
        self.font_h2 = get_safe_font("segoeui", 16, bold=True)
        self.font_body = get_safe_font("segoeui", 13)
        self.font_btn = get_safe_font("segoeui", 13, bold=True)
        self.font_small = get_safe_font("segoeui", 11)
        self.font_stage_badge = get_safe_font("segoeui", 14, bold=True)
        self.font_stage_huge = get_safe_font("segoeui", 42, bold=True)
        self.font_stage_sub = get_safe_font("segoeui", 14)

        # Trạng thái game hiện tại
        self.map_data: Optional[MapData] = None
        self.game_state: Optional[GameState] = None
        self.initial_state: Optional[GameState] = None
        self.move_history: List[GameState] = []
        self.game_over = False
        self.game_won = False

        # Trạng thái chuyển màn (Stage Transition)
        self.transition_active = False
        self.transition_timer = 0.0
        self.transition_duration = 1.8
        self.next_stage_title = ""
        self.next_stage_subtitle = ""
        self.is_all_cleared = False

        # Trạng thái giải thuật và Replay
        self.search_result: Optional[SearchResult] = None
        self.is_searching = False
        self.search_thread: Optional[threading.Thread] = None

        self.replay_states: List[GameState] = []
        self.replay_actions: List[Any] = []
        self.replay_idx = 0
        self.is_playing_replay = False
        self.replay_speed = 0.25  # Giây mỗi bước
        self.last_replay_time = 0.0

        # Nút bấm giao diện
        self.buttons: List[Button] = []
        self._init_buttons()

        # Tải màn chơi ban đầu
        self.load_level(0)

    def _init_buttons(self):
        """Khởi tạo toàn bộ các nút điều khiển trên Sidebar."""
        self.buttons.clear()
        panel_x = 830

        # Nhóm 1: Chọn màn chơi & Cửa sổ
        self.btn_fullscreen = Button(
            pygame.Rect(1120, 12, 115, 26), "Fullscreen",
            self.toggle_fullscreen, self.font_small,
            bg_color=(35, 45, 65), hover_color=(55, 70, 100)
        )
        self.buttons.append(self.btn_fullscreen)

        self.buttons.append(Button(
            pygame.Rect(panel_x, 50, 60, 30), "< Prev",
            self.prev_level, self.font_btn
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 70, 50, 100, 30), "New Game",
            self.new_game, self.font_btn, bg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 180, 50, 100, 30), "Restart",
            self.restart_level, self.font_btn, bg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 290, 50, 60, 30), "Next >",
            self.next_level, self.font_btn
        ))

        # Nhóm 2: Các nút giải thuật toán
        algo_y = 135
        btn_w = 95
        btn_h = 32
        spacing = 8

        self.buttons.append(Button(
            pygame.Rect(panel_x, algo_y, btn_w, btn_h), "Solve BFS",
            lambda: self.start_solver("BFS"), self.font_btn,
            bg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + (btn_w + spacing), algo_y, btn_w, btn_h), "Solve DFS",
            lambda: self.start_solver("DFS"), self.font_btn,
            bg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 2 * (btn_w + spacing), algo_y, btn_w, btn_h), "Solve UCS",
            lambda: self.start_solver("UCS"), self.font_btn,
            bg_color=BTN_PRIMARY, hover_color=BTN_PRIMARY_HOVER
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 3 * (btn_w + spacing), algo_y, btn_w, btn_h), "Solve A*",
            lambda: self.start_solver("A*"), self.font_btn,
            bg_color=BTN_SUCCESS, hover_color=BTN_SUCCESS_HOVER
        ))

        # Nhóm 3: Điều khiển Replay lời giải
        replay_y = 390
        self.btn_play_pause = Button(
            pygame.Rect(panel_x, replay_y, 90, 30), "> Play",
            self.toggle_play_replay, self.font_btn
        )
        self.buttons.append(self.btn_play_pause)

        self.buttons.append(Button(
            pygame.Rect(panel_x + 100, replay_y, 75, 30), "< Back",
            self.step_backward_replay, self.font_btn
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 185, replay_y, 75, 30), "Step >",
            self.step_forward_replay, self.font_btn
        ))

        # Tốc độ chiếu
        self.buttons.append(Button(
            pygame.Rect(panel_x + 275, replay_y, 50, 30), "1x",
            lambda: self.set_speed(0.3), self.font_btn
        ))
        self.buttons.append(Button(
            pygame.Rect(panel_x + 335, replay_y, 50, 30), "2x",
            lambda: self.set_speed(0.12), self.font_btn
        ))

    def load_level(self, idx: int):
        """Tải một màn chơi từ danh sách file."""
        if not self.level_files:
            return
        self.current_level_idx = idx % len(self.level_files)
        file_path = self.level_files[self.current_level_idx]

        self.map_data = load_map_from_file(file_path)
        self.renderer.compute_layout(self.map_data, view_w=820, view_h=self.height)
        init_block = BlockState(
            Orientation.STANDING,
            self.map_data.start_pos[0],
            self.map_data.start_pos[1]
        )
        self.initial_state = GameState(
            init_block,
            self.map_data.initial_bridges,
            self.map_data
        )
        self.game_state = self.initial_state
        self.move_history = [self.initial_state]
        self.game_over = False
        self.game_won = False
        self.transition_active = False
        self.transition_timer = 0.0
        self.is_all_cleared = False
        self.search_result = None
        self.replay_states = []
        self.replay_actions = []
        self.replay_idx = 0
        self.is_playing_replay = False
        self.animator.reset()
        self.board_animator.reset()

    def restart_level(self):
        """Khởi động lại màn chơi hiện tại."""
        if self.map_data:
            init_block = BlockState(
                Orientation.STANDING,
                self.map_data.start_pos[0],
                self.map_data.start_pos[1]
            )
            self.initial_state = GameState(
                init_block,
                self.map_data.initial_bridges,
                self.map_data
            )
            self.game_state = self.initial_state
            self.move_history = [self.initial_state]
            self.game_over = False
            self.game_won = False
            self.transition_active = False
            self.transition_timer = 0.0
            self.replay_idx = 0
            self.is_playing_replay = False
            self.animator.reset()
            self.board_animator.reset()

    def start_board_restart_sequence(self):
        """Khởi động chuỗi hoạt ảnh tái lập màn chơi (Board Disintegrate & Rebuild)."""
        self.animator.reset()
        self.game_over = False
        self.game_won = False
        self.transition_active = False
        self.is_playing_replay = False

        # Khôi phục trạng thái ban đầu của bàn cờ và khối Bloxorz
        if self.map_data:
            init_block = BlockState(
                Orientation.STANDING,
                self.map_data.start_pos[0],
                self.map_data.start_pos[1]
            )
            self.initial_state = GameState(
                init_block,
                self.map_data.initial_bridges,
                self.map_data
            )
            self.game_state = self.initial_state
            self.move_history = [self.initial_state]

        def on_rebuild_complete():
            self.restart_level()

        self.board_animator.start(self.map_data, on_complete=on_rebuild_complete)

    def new_game(self):
        """New Game: quay về màn đầu tiên và bắt đầu chơi lại từ đầu."""
        self.load_level(0)

    def next_level(self):
        self.load_level(self.current_level_idx + 1)

    def prev_level(self):
        self.load_level(self.current_level_idx - 1)

    def undo_move(self):
        """Lùi lại một bước đi thủ công."""
        self.animator.reset()
        self.transition_active = False
        self.transition_timer = 0.0
        if len(self.move_history) > 1:
            self.move_history.pop()
            self.game_state = self.move_history[-1]
            self.game_over = False
            self.game_won = self.game_state.is_goal()

    def trigger_stage_transition(self):
        """Kích hoạt màn hình chuyển cảnh sau khi khối đã chìm sâu và biến mất trong lỗ đích."""
        self.game_won = True
        next_idx = self.current_level_idx + 1
        if next_idx < len(self.level_files):
            filename = os.path.basename(self.level_files[next_idx])
            match = re.search(r'\d+', filename)
            if match:
                num = int(match.group())
                self.next_stage_title = f"MÀN {num:02d}"
            else:
                self.next_stage_title = f"MÀN {next_idx + 1:02d}"
            self.next_stage_subtitle = "Chuẩn bị bước vào màn chơi tiếp theo..."
            self.is_all_cleared = False
        else:
            self.next_stage_title = "HOÀN THÀNH TẤT CẢ MÀN CHƠI!"
            self.next_stage_subtitle = "Chúc mừng bạn đã phá đảo toàn bộ 33 màn Bloxorz!"
            self.is_all_cleared = True

        self.transition_active = True
        self.transition_timer = 0.0

    def start_solver(self, algo_name: str):
        """Kích hoạt chạy thuật toán tìm kiếm trên một luồng nền riêng biệt."""
        if self.is_searching or not self.initial_state:
            return

        self.is_searching = True
        self.search_result = None
        self.is_playing_replay = False
        self.game_over = False
        self.game_won = False

        def worker():
            res = None
            if algo_name == "BFS":
                res = solve_bfs(self.initial_state)
            elif algo_name == "DFS":
                res = solve_dfs(self.initial_state)
            elif algo_name == "UCS":
                res = solve_ucs(self.initial_state, weighted=True)
            elif algo_name == "A*":
                # A* dùng CÙNG hàm chi phí với UCS để so sánh công bằng
                res = solve_astar(self.initial_state, heuristic_type="relaxed_grid", weighted=True)

            self.search_result = res
            self.is_searching = False

            if res and res.success:
                self.replay_states = res.states
                self.replay_actions = res.actions
                self.replay_idx = 0
                self.is_playing_replay = True
                self.last_replay_time = time.time()
                # Cập nhật trạng thái hiển thị
                if self.replay_states:
                    self.game_state = self.replay_states[0]

        self.search_thread = threading.Thread(target=worker, daemon=True)
        self.search_thread.start()

    def toggle_play_replay(self):
        if not self.replay_states:
            return
        if self.animator.is_animating():
            self.animator.finish_now()
        self.is_playing_replay = not self.is_playing_replay
        self.last_replay_time = time.time()
        self.btn_play_pause.text = "|| Pause" if self.is_playing_replay else "> Play"

    def step_forward_replay(self):
        if not self.replay_states or self.replay_idx >= len(self.replay_states) - 1:
            return
        if self.animator.is_animating():
            self.animator.finish_now()

        action = self.replay_actions[self.replay_idx]
        nxt_state = self.replay_states[self.replay_idx + 1]
        cur_block = self.replay_states[self.replay_idx].block

        c_idx = 0
        act_dir = None
        if isinstance(action, Direction):
            act_dir = action
        elif isinstance(action, tuple) and len(action) == 2:
            c_idx, act_dir = action

        if act_dir:
            def on_forward_step_done():
                self.replay_idx += 1
                self.game_state = nxt_state
                if nxt_state.is_goal():
                    self.animator.start_fall_goal(
                        nxt_state.block,
                        self.map_data.goal_pos,
                        duration=0.8,
                        on_complete=self.trigger_stage_transition
                    )
                else:
                    self.game_won = False

            self.animator.start_roll(
                cur_block,
                act_dir,
                cube_index=c_idx,
                duration=0.15,
                on_complete=on_forward_step_done
            )
        else:
            self.replay_idx += 1
            self.game_state = nxt_state
            self.game_won = self.game_state.is_goal()

    def step_backward_replay(self):
        self.animator.reset()
        if self.replay_states and self.replay_idx > 0:
            self.replay_idx -= 1
            self.game_state = self.replay_states[self.replay_idx]
            self.game_won = self.game_state.is_goal()

    def toggle_fullscreen(self):
        """Bật/tắt chế độ phóng to toàn màn hình (Fullscreen / Maximize)."""
        self.is_fullscreen = not self.is_fullscreen
        pygame.display.toggle_fullscreen()
        if hasattr(self, "btn_fullscreen"):
            self.btn_fullscreen.text = "Windowed" if self.is_fullscreen else "Fullscreen"

    def set_speed(self, speed: float):
        self.replay_speed = speed

    def handle_manual_move(self, direction: Direction):
        """Thực hiện lăn khối khi người chơi bấm phím điều khiển."""
        if self.game_over or self.game_won or not self.game_state or self.board_animator.is_animating():
            return

        # Nếu đang có animation dở:
        if self.animator.is_animating():
            # Nếu đang rơi vực thẳm hoặc rơi vào đích thì bỏ qua phím di chuyển
            if self.animator.state != BlockAnimator.STATE_ROLLING:
                return
            # Chỉ hoàn tất nhanh khi đang lăn thông thường để tránh nghẽn phím
            self.animator.finish_now()
            if self.game_over or self.game_won:
                return

        current_block = self.game_state.block
        active_idx = 0
        if current_block.orientation != Orientation.SPLIT:
            nxt = self.game_state.transition(direction)
        else:
            active_idx = current_block.active_cube
            nxt = self.game_state.transition((active_idx, direction))

        if nxt is not None:
            # Di chuyển hợp lệ -> kích hoạt rolling animation
            def on_manual_roll_done():
                self.game_state = nxt
                self.move_history.append(nxt)
                if nxt.is_goal():
                    self.animator.start_fall_goal(
                        nxt.block,
                        self.map_data.goal_pos,
                        duration=0.8,
                        on_complete=self.trigger_stage_transition
                    )

            self.animator.start_roll(
                current_block,
                direction,
                cube_index=active_idx,
                duration=0.15,
                on_complete=on_manual_roll_done
            )
        else:
            # Di chuyển thất bại -> kiểm tra rơi do ô cam vỡ hay rơi mép sàn
            is_fragile = False
            fragile_cell = None
            if current_block.orientation != Orientation.SPLIT:
                try:
                    test_rolled = current_block.roll(direction)
                    if test_rolled.orientation == Orientation.STANDING:
                        r, c = test_rolled.r, test_rolled.c
                        if 0 <= r < self.map_data.rows and 0 <= c < self.map_data.cols:
                            if self.map_data.board[r][c] == 2:
                                is_fragile = True
                                fragile_cell = (r, c)
                except Exception:
                    pass

            def on_fall_done():
                # Khi rơi xong (thua cuộc) -> kích hoạt chuỗi hoạt ảnh tái lập màn chơi
                self.start_board_restart_sequence()

            if is_fragile and fragile_cell:
                self.animator.start_fall_fragile(
                    current_block,
                    fragile_cell,
                    duration=0.65,
                    on_complete=on_fall_done
                )
            else:
                self.animator.start_fall_edge(
                    current_block,
                    direction,
                    cube_index=active_idx,
                    duration=0.65,
                    on_complete=on_fall_done
                )


    def run(self):
        """Vòng lặp chính xử lý sự kiện và vẽ khung hình (Frame Loop)."""
        running = True
        pulse_val = 0.0

        while running:
            dt = self.clock.tick(60) / 1000.0
            pulse_val += dt
            mouse_pos = pygame.mouse.get_pos()

            # Cập nhật tiến trình Animation mỗi frame
            self.animator.update(dt)
            self.board_animator.update(dt)

            # Cập nhật chuyển màn tự động
            if self.transition_active:
                self.transition_timer += dt
                if self.transition_timer >= self.transition_duration:
                    self.transition_active = False
                    if not self.is_all_cleared:
                        self.next_level()

            # 1. Cập nhật Replay tự động nếu đang bật
            if self.is_playing_replay and self.replay_states:
                now = time.time()
                if not self.animator.is_animating() and (now - self.last_replay_time >= self.replay_speed):
                    self.last_replay_time = now
                    if self.replay_idx < len(self.replay_states) - 1:
                        action = self.replay_actions[self.replay_idx]
                        nxt_state = self.replay_states[self.replay_idx + 1]
                        cur_block = self.replay_states[self.replay_idx].block

                        c_idx = 0
                        act_dir = None
                        if isinstance(action, Direction):
                            act_dir = action
                        elif isinstance(action, tuple) and len(action) == 2:
                            c_idx, act_dir = action

                        if act_dir:
                            roll_dur = min(0.18, max(0.06, self.replay_speed * 0.75))

                            def on_auto_step_done():
                                self.replay_idx += 1
                                self.game_state = nxt_state
                                if nxt_state.is_goal():
                                    self.is_playing_replay = False
                                    self.btn_play_pause.text = "> Play"
                                    self.animator.start_fall_goal(
                                        nxt_state.block,
                                        self.map_data.goal_pos,
                                        duration=0.8,
                                        on_complete=self.trigger_stage_transition
                                    )

                            self.animator.start_roll(
                                cur_block,
                                act_dir,
                                cube_index=c_idx,
                                duration=roll_dur,
                                on_complete=on_auto_step_done
                            )
                        else:
                            self.replay_idx += 1
                            self.game_state = nxt_state
                            if self.game_state.is_goal():
                                self.game_won = True
                                self.is_playing_replay = False
                                self.btn_play_pause.text = "> Play"
                    else:
                        self.is_playing_replay = False
                        self.btn_play_pause.text = "> Play"

            # 2. Xử lý sự kiện (Events)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                # Nếu đang trong màn hình chuyển cảnh, phím bấm hoặc click trên bàn cờ sẽ chuyển ngay
                if self.transition_active:
                    if event.type == pygame.KEYDOWN:
                        self.transition_active = False
                        if not self.is_all_cleared:
                            self.next_level()
                        continue
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if event.pos[0] < 820:
                            self.transition_active = False
                            if not self.is_all_cleared:
                                self.next_level()
                            continue

                # Nếu đang trong hoạt ảnh tái lập màn chơi, phím bấm hoặc click sẽ bỏ qua ngay
                if self.board_animator.is_animating():
                    if event.type == pygame.KEYDOWN:
                        self.board_animator.skip_to_end()
                        continue
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if event.pos[0] < 820:
                            self.board_animator.skip_to_end()
                            continue

                # Nút bấm UI
                for btn in self.buttons:
                    btn.handle_event(event)

                # Phím điều khiển bàn phím (Manual Keyboard Control)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_F11 or (event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_ALT)):
                        self.toggle_fullscreen()
                    elif event.key == pygame.K_ESCAPE and self.is_fullscreen:
                        self.toggle_fullscreen()
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        self.handle_manual_move(Direction.UP)
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        self.handle_manual_move(Direction.DOWN)
                    elif event.key in (pygame.K_LEFT, pygame.K_a):
                        self.handle_manual_move(Direction.LEFT)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        self.handle_manual_move(Direction.RIGHT)
                    elif event.key == pygame.K_SPACE:
                        # Đổi khối phân thân đang điều khiển (tạo trạng thái mới, không sửa trạng thái cũ)
                        if self.game_state and self.game_state.block.orientation == Orientation.SPLIT:
                            if self.animator.is_animating():
                                self.animator.finish_now()
                            old = self.game_state.block
                            swapped = BlockState(
                                Orientation.SPLIT, old.r, old.c, old.r1, old.c1,
                                active_cube=1 - old.active_cube
                            )
                            self.game_state = GameState(
                                swapped, self.game_state.bridge_state, self.map_data
                            )
                            if len(self.move_history) > 0 and not self.replay_states:
                                self.move_history[-1] = self.game_state
                    elif event.key == pygame.K_r:
                        self.restart_level()
                    elif event.key == pygame.K_u:
                        self.undo_move()

                elif event.type == pygame.VIDEORESIZE:
                    # Pygame SCALED tự động nội suy tỷ lệ hiển thị khi kéo phóng to cửa sổ
                    pass

            # 3. Cập nhật trạng thái chuột trên các nút
            for btn in self.buttons:
                btn.update(mouse_pos)

            # 4. Vẽ nền và khung cảnh 3D Isometric
            self.screen.fill(BG_COLOR)
            self.renderer.render_background(self.screen, width=820, height=self.height)

            # Vẽ sàn và khối Bloxorz
            if self.map_data and self.game_state:
                origin_x = self.renderer.origin_x
                origin_y = self.renderer.origin_y

                self.renderer.render_board(
                    self.map_data,
                    self.game_state.bridge_state,
                    origin_x,
                    origin_y,
                    tile_offsets=self.board_animator.tile_offsets if self.board_animator.is_animating() else None,
                    hidden_tiles=self.board_animator.hidden_tiles if self.board_animator.is_animating() else None
                )

                if self.board_animator.is_animating():
                    if self.board_animator.should_render_block():
                        z_off = self.board_animator.get_spawn_z_offset()
                        self.renderer.render_block(
                            self.game_state.block,
                            origin_x,
                            origin_y,
                            pulse_val=pulse_val,
                            z_offset=z_off
                        )
                elif self.animator.is_animating():
                    self.animator.render(
                        self.screen,
                        origin_x,
                        origin_y,
                        self.renderer
                    )
                elif not self.game_over and not self.game_won and not self.transition_active:
                    self.renderer.render_block(
                        self.game_state.block,
                        origin_x,
                        origin_y,
                        pulse_val=pulse_val
                    )

                # Vẽ hiệu ứng phụ (mảnh vỡ sàn nứt vỡ, quầng sáng đích)
                self.animator.render_overlays(
                    self.screen,
                    origin_x,
                    origin_y,
                    self.renderer
                )

                # Vẽ lớp overlay của hoạt ảnh tái lập sàn (Màn hình chờ, Flash chớp sáng)
                if self.board_animator.is_animating():
                    self.board_animator.render_overlay(self.screen, 820, self.height)


            # 5. Vẽ thông báo trạng thái Game hoặc Màn hình chuyển cảnh
            if self.board_animator.is_animating():
                pass
            elif self.transition_active:
                self._render_stage_transition()
            elif self.game_won:
                self._draw_status_banner("CHIẾN THẮNG! (STAGE CLEARED!)", TEXT_SUCCESS)
            elif self.animator.state in (BlockAnimator.STATE_FALL_EDGE, BlockAnimator.STATE_FALL_FRAGILE):
                self._draw_status_banner("RƠI SÀN! ĐANG KHỞI ĐỘNG LẠI...", TEXT_DANGER)
            elif self.is_searching:
                self._draw_status_banner("ĐANG TÌM KIẾM LỜI GIẢI...", TEXT_ACCENT)

            # 6. Vẽ thanh Sidebar điều khiển bên phải
            self._render_sidebar()

            pygame.display.flip()

        pygame.quit()

    def _render_stage_transition(self):
        """Vẽ giao diện modal chuyển màn nổi bật sau khi hoàn thành màn chơi."""
        if not self.transition_active:
            return

        # Lớp phủ mờ nền bàn cờ (0 -> 820px)
        fade_alpha = int(min(215, 215 * (self.transition_timer / 0.22)))
        overlay = pygame.Surface((820, self.height), pygame.SRCALPHA)
        overlay.fill((10, 14, 24, fade_alpha))
        self.screen.blit(overlay, (0, 0))

        # Hộp thông báo trung tâm
        card_w, card_h = 460, 230
        card_x = (820 - card_w) // 2
        card_y = (self.height - card_h) // 2 - 20
        card_rect = pygame.Rect(card_x, card_y, card_w, card_h)

        # Vẽ nền hộp thông báo
        pygame.draw.rect(self.screen, (20, 26, 38), card_rect, border_radius=16)
        border_col = (255, 205, 60) if not self.is_all_cleared else (63, 185, 80)
        pygame.draw.rect(self.screen, border_col, card_rect, width=2, border_radius=16)

        # 1. Badge phía trên
        badge_text = "★ CHIẾN THẮNG MÀN HIỆN TẠI ★" if not self.is_all_cleared else "★ XUẤT SẮC! PHÁ ĐẢO TOÀN BỘ ★"
        badge_surf = self.font_stage_badge.render(badge_text, True, border_col)
        badge_rect = badge_surf.get_rect(center=(card_rect.centerx, card_rect.y + 35))
        self.screen.blit(badge_surf, badge_rect)

        # 2. Tiêu đề màn tiếp theo ("MÀN 02"...)
        title_col = (255, 255, 255)
        title_surf = self.font_stage_huge.render(self.next_stage_title, True, title_col)
        title_rect = title_surf.get_rect(center=(card_rect.centerx, card_rect.y + 85))
        self.screen.blit(title_surf, title_rect)

        # 3. Phụ đề
        sub_surf = self.font_stage_sub.render(self.next_stage_subtitle, True, TEXT_MUTED)
        sub_rect = sub_surf.get_rect(center=(card_rect.centerx, card_rect.y + 130))
        self.screen.blit(sub_surf, sub_rect)

        # 4. Thanh tiến trình đếm giờ chuyển màn (Progress Bar)
        bar_w, bar_h = 340, 6
        bar_x = card_rect.centerx - bar_w // 2
        bar_y = card_rect.y + 165
        pygame.draw.rect(self.screen, (35, 45, 65), (bar_x, bar_y, bar_w, bar_h), border_radius=3)

        progress = min(1.0, self.transition_timer / self.transition_duration)
        fill_w = int(bar_w * progress)
        if fill_w > 0:
            pygame.draw.rect(self.screen, border_col, (bar_x, bar_y, fill_w, bar_h), border_radius=3)

        # 5. Gợi ý phím bấm
        hint_surf = self.font_small.render("(Bấm phím bất kỳ hoặc Space / Enter để tiếp tục ngay)", True, (130, 145, 170))
        hint_rect = hint_surf.get_rect(center=(card_rect.centerx, card_rect.y + 195))
        self.screen.blit(hint_surf, hint_rect)

    def _draw_status_banner(self, text: str, color: Tuple[int, int, int]):
        """Vẽ biểu ngữ trạng thái nổi bật phía trên bàn cờ."""
        banner_rect = pygame.Rect(180, 20, 460, 40)
        pygame.draw.rect(self.screen, (22, 27, 38, 220), banner_rect, border_radius=8)
        pygame.draw.rect(self.screen, color, banner_rect, width=2, border_radius=8)

        txt_surf = self.font_h2.render(text, True, color)
        txt_rect = txt_surf.get_rect(center=banner_rect.center)
        self.screen.blit(txt_surf, txt_rect)

    def _render_sidebar(self):
        """Vẽ toàn bộ bảng thông tin, số liệu tìm kiếm và các nút bấm trên Sidebar."""
        sidebar_rect = pygame.Rect(820, 0, self.width - 820, self.height)
        pygame.draw.rect(self.screen, PANEL_BG, sidebar_rect)
        pygame.draw.line(self.screen, PANEL_BORDER, (820, 0), (820, self.height), 2)

        x = 835
        # Tiêu đề màn chơi
        stage_name = self.map_data.map_name if self.map_data else "Unknown"
        title_surf = self.font_title.render(f"Bloxorz Solver: {stage_name}", True, TEXT_WHITE)
        self.screen.blit(title_surf, (x, 15))

        # Tiêu đề nhóm thuật toán
        h_algo = self.font_h2.render("Chọn Thuật Toán Tìm Kiếm:", True, TEXT_WHITE)
        self.screen.blit(h_algo, (x, 105))

        # Khung thẻ hiển thị số liệu đo lường (Metrics Card)
        card_rect = pygame.Rect(x, 185, 395, 185)
        pygame.draw.rect(self.screen, (18, 22, 32), card_rect, border_radius=8)
        pygame.draw.rect(self.screen, PANEL_BORDER, card_rect, width=1, border_radius=8)

        card_title = self.font_h2.render("Thông Số Đánh Giá Thuật Toán:", True, TEXT_ACCENT)
        self.screen.blit(card_title, (x + 12, 195))

        if self.search_result:
            r = self.search_result
            status_text = "Thành công" if r.success else "Thất bại"
            status_color = TEXT_SUCCESS if r.success else TEXT_DANGER

            lines = [
                ("Thuật toán:", r.algorithm, TEXT_WHITE),
                ("Trạng thái:", status_text, status_color),
                ("Thời gian tìm kiếm (Time):", f"{r.search_time:.4f} s ({r.search_time * 1000:.1f} ms)", TEXT_WHITE),
                ("Bộ nhớ tiêu thụ đỉnh (Peak Mem):", f"{r.peak_memory_kb:.2f} KB", TEXT_WHITE),
                ("Số nút mở rộng (Expanded Nodes):", f"{r.expanded_nodes}", TEXT_WARN),
                ("Độ dài giải pháp (Solution Length):", f"{r.solution_length} bước", TEXT_SUCCESS),
                ("Tổng chi phí đường đi (Cost):", f"{r.solution_cost:.2f}", TEXT_WHITE)
            ]

            line_y = 222
            for label, val, val_color in lines:
                lbl_surf = self.font_body.render(label, True, TEXT_MUTED)
                val_surf = self.font_body.render(val, True, val_color)
                self.screen.blit(lbl_surf, (x + 15, line_y))
                self.screen.blit(val_surf, (x + 230, line_y))
                line_y += 20
        else:
            hint = self.font_body.render("Chưa có kết quả. Bấm các nút Solve phía trên.", True, TEXT_MUTED)
            self.screen.blit(hint, (x + 15, 230))

        # Tiêu đề nhóm Replay
        h_rep = self.font_h2.render("Trình Chiếu Lời Giải:", True, TEXT_WHITE)
        self.screen.blit(h_rep, (x, 435))

        if self.replay_states:
            prog_text = f"Bước hiện tại: {self.replay_idx} / {len(self.replay_states) - 1}"
            prog_surf = self.font_btn.render(prog_text, True, TEXT_WARN)
            self.screen.blit(prog_surf, (x + 230, 435))

            # Danh sách các nước đi tìm được
            moves_box = pygame.Rect(x, 465, 395, 180)
            pygame.draw.rect(self.screen, (18, 22, 32), moves_box, border_radius=6)
            pygame.draw.rect(self.screen, PANEL_BORDER, moves_box, width=1, border_radius=6)

            # Liệt kê các bước
            start_step = max(0, self.replay_idx - 3)
            end_step = min(len(self.replay_actions), start_step + 7)

            item_y = 472
            for s_idx in range(start_step, end_step):
                act = self.replay_actions[s_idx]
                act_str = act.value if hasattr(act, 'value') else str(act)
                is_curr = (s_idx == self.replay_idx - 1)
                color = TEXT_ACCENT if is_curr else TEXT_WHITE
                if isinstance(act, tuple):
                    act_str = f"Cube {act[0] + 1}: {act[1].value}"
                prefix = "> " if is_curr else "   "

                txt = f"{prefix}Bước {s_idx + 1}: {act_str}"
                surf = self.font_body.render(txt, True, color)
                self.screen.blit(surf, (x + 12, item_y))
                item_y += 22
        else:
            hint_rep = self.font_body.render("Khi giải xong, bạn có thể chạy tua hoặc đi từng bước.", True, TEXT_MUTED)
            self.screen.blit(hint_rep, (x, 465))

        # Hướng dẫn phím bấm thủ công dưới đáy
        guide_y = 665
        pygame.draw.line(self.screen, PANEL_BORDER, (x, guide_y), (x + 395, guide_y), 1)
        h_guide = self.font_btn.render("Phím chơi thủ công:", True, TEXT_ACCENT)
        self.screen.blit(h_guide, (x, guide_y + 8))

        guide_lines = [
            "- Mũi tên / WASD: Lăn khối Bloxorz",
            "- Phím Space: Chuyển đổi khối điều khiển khi phân thân",
            "- Tự động chơi lại khi rơi sàn | Phím U: Hoàn tác (Undo)"
        ]
        gy = guide_y + 30
        for gl in guide_lines:
            gsurf = self.font_small.render(gl, True, TEXT_MUTED)
            self.screen.blit(gsurf, (x, gy))
            gy += 18

        # Vẽ tất cả nút bấm
        for btn in self.buttons:
            btn.draw(self.screen)
