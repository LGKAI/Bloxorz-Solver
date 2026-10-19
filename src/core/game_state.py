"""
Module: game_state.py
Mô tả: Quản lý trạng thái toàn vẹn của trò chơi Bloxorz:
      kết hợp trạng thái khối (BlockState), cấu hình các cầu nối động (bridge_state),
      các quy tắc chuyển trạng thái khi lăn khối/kích hoạt công tắc, kiểm tra thắng/thua,
      và hàm tính chi phí bước đi (cost function) cho UCS.
"""

from typing import List, Tuple, Optional, Any, Union
from src.core.block import BlockState, Orientation, Direction
from src.core.map_loader import MapData


class GameState:
    """
    Đại diện cho trạng thái của một nút trong không gian tìm kiếm:
    - block: Vị trí và hướng của khối hộp (BlockState)
    - bridge_state: Tuple các giá trị boolean đại diện cho trạng thái Đóng (False) / Mở (True)
                    của từng cầu nối trong bản đồ.
    - map_data: Dữ liệu tĩnh của màn chơi (bản đồ, công tắc, vị trí đích...)
    """

    def __init__(
        self,
        block: BlockState,
        bridge_state: Tuple[bool, ...],
        map_data: MapData
    ):
        self.block = block
        self.bridge_state = bridge_state
        self.map_data = map_data
        self._canonical_key: Optional[tuple] = None

    def canonical_key(self) -> tuple:
        """
        Khóa băm chuẩn hóa của trạng thái để lưu vào Visited / Closed Set.
        Bao gồm: (canonical_key của block, bridge_state).
        Thời gian so sánh và băm O(1).
        """
        if self._canonical_key is None:
            self._canonical_key = (self.block.canonical_key(), self.bridge_state)
        return self._canonical_key

    def is_goal(self) -> bool:
        """
        Kiểm tra điều kiện chiến thắng:
        Khối phải ở trạng thái ĐỨNG THẲNG (STANDING) đúng ngay tại vị trí lỗ đích (giá trị 9).
        Khối nằm đè lên đích hoặc khối phân thân không được tính là chiến thắng.
        """
        if self.block.orientation != Orientation.STANDING:
            return False
        return (self.block.r, self.block.c) == self.map_data.goal_pos

    def is_cell_walkable(self, r: int, c: int, bridge_tuple: Tuple[bool, ...]) -> bool:
        """
        Kiểm tra xem một ô (r, c) có thể đi lên được hay không (không phải hư vô):
        - Nếu là ô cầu nối: kiểm tra cầu đó đang mở hay đóng.
        - Nếu là ô sàn thông thường: kiểm tra giá trị ma trận > 0.
        """
        if not (0 <= r < self.map_data.rows and 0 <= c < self.map_data.cols):
            return False

        if (r, c) in self.map_data.bridge_indices:
            idx = self.map_data.bridge_indices[(r, c)]
            return bridge_tuple[idx]

        return self.map_data.board[r][c] != 0

    def get_valid_actions(self) -> List[Any]:
        """
        Trả về danh sách các hành động có thể thử tại trạng thái hiện tại:
        - Khối đơn: [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        - Khối phân thân: [('CUBE_0', dir), ('CUBE_1', dir)] với 4 hướng cho từng khối.
        """
        if self.block.orientation != Orientation.SPLIT:
            return [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        else:
            actions = []
            for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
                actions.append((0, d))  # Khối lập phương 1
            for d in [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]:
                actions.append((1, d))  # Khối lập phương 2
            return actions

    def transition(self, action: Any) -> Optional["GameState"]:
        """
        Mô hình chuyển trạng thái (Transition Model):
        Nhận vào một hành động (Direction hoặc (cube_idx, Direction)),
        trả về trạng thái kế tiếp (GameState) nếu nước đi hợp lệ, hoặc None nếu khối rơi khỏi sàn/bị vỡ.
        """
        # 1. Thực hiện di chuyển tọa độ khối
        was_split = (self.block.orientation == Orientation.SPLIT)
        moved_cell = None  # Ô mà khối lập phương vừa di chuyển bước lên (chỉ dùng khi đang phân thân)

        if not was_split:
            if not isinstance(action, Direction):
                return None
            new_block = self.block.roll(action)
        else:
            if not (isinstance(action, tuple) and len(action) == 2):
                return None
            cube_idx, direction = action
            new_block = self.block.move_cube(cube_idx, direction)

            # Hai khối lập phương không được chồng lên cùng một ô
            if (new_block.orientation == Orientation.SPLIT
                    and (new_block.r, new_block.c) == (new_block.r1, new_block.c1)):
                return None

            # Tính ô đích của khối vừa di chuyển (tính trước khi có thể bị sáp nhập)
            deltas = {
                Direction.UP: (-1, 0), Direction.DOWN: (1, 0),
                Direction.LEFT: (0, -1), Direction.RIGHT: (0, 1)
            }
            base_r, base_c = (self.block.r, self.block.c) if cube_idx == 0 else (self.block.r1, self.block.c1)
            moved_cell = (base_r + deltas[direction][0], base_c + deltas[direction][1])

        # 2. Kiểm tra tính hợp lệ cơ bản (không nằm lọt ra ngoài hoặc trên ô hư vô / cầu đóng)
        cells = new_block.occupied_cells()
        for r, c in cells:
            if not self.is_cell_walkable(r, c, self.bridge_state):
                return None  # Rơi xuống hư vô hoặc cầu đang đóng

        # 3. Kiểm tra quy tắc ô cam dễ vỡ (Fragile Tile - giá trị 2):
        # Khối chỉ rơi vỡ nếu đứng thẳng (STANDING) toàn bộ trọng lượng lên ô cam.
        # Khối nằm (HORIZONTAL, VERTICAL) hoặc khối phân thân 1x1x1 (nửa trọng lượng) thì an toàn.
        if new_block.orientation == Orientation.STANDING:
            r, c = new_block.r, new_block.c
            if (r, c) not in self.map_data.bridge_indices:
                if self.map_data.board[r][c] == 2:
                    return None  # Ô cam bị sập, khối rơi xuống

        # 4. Kích hoạt công tắc (Switches) và cập nhật trạng thái các cầu nối
        bridges_list = list(self.bridge_state)

        if was_split:
            # Đang phân thân: CHỈ khối lập phương vừa di chuyển mới kích hoạt công tắc,
            # và chỉ là công tắc nhẹ (4, 5, 6). Việc sáp nhập không kích hoạt lại công tắc
            # (tránh toggle bị áp dụng 2 lần).
            sw = self.map_data.switches.get(moved_cell)
            if sw is not None and sw.tile_type in (4, 5, 6):
                self._apply_switch_bridges(sw, bridges_list)

        elif new_block.orientation == Orientation.STANDING:
            # Khối đứng thẳng: kích hoạt được mọi loại công tắc
            r, c = new_block.r, new_block.c
            sw = self.map_data.switches.get((r, c))
            if sw is not None:
                # Công tắc phân thân (tile 7): dịch chuyển và tách thành 2 khối 1x1x1
                if sw.tile_type == 7 and sw.split_targets:
                    t1, t2 = sw.split_targets
                    new_block = BlockState(
                        Orientation.SPLIT,
                        t1[0], t1[1],
                        t2[0], t2[1],
                        active_cube=0
                    ).check_merge()

                # Công tắc tác động cầu nối (3, 4, 5, 6, 8)
                self._apply_switch_bridges(sw, bridges_list)

        else:
            # Khối nằm (HORIZONTAL / VERTICAL): chỉ kích hoạt công tắc nhẹ (4, 5, 6).
            # Công tắc nặng (3, 8) và phân thân (7) KHÔNG bị kích hoạt khi nằm.
            for r, c in cells:
                sw = self.map_data.switches.get((r, c))
                if sw is not None and sw.tile_type in (4, 5, 6):
                    self._apply_switch_bridges(sw, bridges_list)

        new_bridge_state = tuple(bridges_list)

        # 6. Kiểm tra lại xem sau khi kích hoạt công tắc, các ô khối đang đứng có bị thụt cầu hay không
        for r, c in new_block.occupied_cells():
            if not self.is_cell_walkable(r, c, new_bridge_state):
                return None  # Cầu bị thụt ngay dưới chân khối -> rơi!

        return GameState(new_block, new_bridge_state, self.map_data)

    def _apply_switch_bridges(self, sw, bridges_list: List[bool]) -> None:
        """Cập nhật trạng thái đảo (toggle), đóng (close), mở (open) cho danh sách cầu nối."""
        for br, bc in sw.toggle_bridges:
            idx = self.map_data.bridge_indices[(br, bc)]
            bridges_list[idx] = not bridges_list[idx]

        for br, bc in sw.close_bridges:
            idx = self.map_data.bridge_indices[(br, bc)]
            bridges_list[idx] = False

        for br, bc in sw.open_bridges:
            idx = self.map_data.bridge_indices[(br, bc)]
            bridges_list[idx] = True

    def calculate_step_cost(self, next_state: "GameState") -> float:
        """
        Hàm chi phí bước đi c(s, a, s') phục vụ thuật toán Uniform-Cost Search (UCS):
        - Chi phí cơ bản cho 1 bước di chuyển: 1.0
        - Phạt rủi ro khi đi vào ô cam dễ vỡ (Fragile tile): +1.0 (tổng cost = 2.0).
          Ý nghĩa trực quan: Ô cam có độ nguy hiểm cao vì hạn chế bước đi kế tiếp và dễ rơi rụng,
          người chơi thận trọng sẽ tránh đi vào ô cam nếu có lộ trình khác an toàn hơn.
        - Chi phí dựng đứng khối (từ nằm sang đứng): +0.2 (tổng cost = 1.2).
          Ý nghĩa cơ học: Nâng trọng tâm chống lại trọng lực tiêu tốn nhiều động năng hơn lăn ngang.
        """
        cost = 1.0

        # Kiểm tra nếu ô đích có ô cam dễ vỡ
        for r, c in next_state.block.occupied_cells():
            if (r, c) not in self.map_data.bridge_indices:
                if self.map_data.board[r][c] == 2:
                    cost += 1.0
                    break

        # Kiểm tra lật từ nằm sang đứng
        if self.block.orientation != Orientation.STANDING and next_state.block.orientation == Orientation.STANDING:
            cost += 0.2

        return cost

    def __hash__(self) -> int:
        return hash(self.canonical_key())

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, GameState):
            return False
        return self.canonical_key() == other.canonical_key()

    def __repr__(self) -> str:
        return f"GameState({self.block}, bridges={self.bridge_state})"
