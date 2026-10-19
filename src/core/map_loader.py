"""
Module: map_loader.py
Mô tả: Đọc và phân tích cú pháp bản đồ Bloxorz từ file định dạng văn bản (.txt)
      hoặc JSON, hỗ trợ đầy đủ 33 màn chơi chuẩn cùng các cơ chế công tắc, cầu nối và phân thân.
"""

import os
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional, Set


@dataclass
class SwitchAction:
    """
    Đại diện cho hành động của một công tắc khi được kích hoạt:
    - tile_type: Loại công tắc (3: Nặng X toggle, 4: Nhẹ tròn đóng, 5: Nhẹ tròn toggle,
                                6: Nhẹ tròn mở, 7: Phân thân, 8: Nặng X mở)
    - toggle_bridges: Danh sách tọa độ (r, c) các cầu cần đảo trạng thái đóng/mở
    - close_bridges: Danh sách tọa độ (r, c) các cầu cần đóng vĩnh viễn / bắt buộc đóng
    - open_bridges: Danh sách tọa độ (r, c) các cầu cần mở vĩnh viễn / bắt buộc mở
    - split_targets: Hai tọa độ đích để dịch chuyển hai khối phân thân ((r1, c1), (r2, c2))
    """
    tile_type: int
    toggle_bridges: List[Tuple[int, int]]
    close_bridges: List[Tuple[int, int]]
    open_bridges: List[Tuple[int, int]]
    split_targets: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None


@dataclass
class MapData:
    """
    Chứa toàn bộ dữ liệu cấu trúc của một màn chơi:
    - rows, cols: Kích thước lưới
    - start_pos: Tọa độ bắt đầu (row, col)
    - goal_pos: Tọa độ đích (row, col)
    - board: Ma trận tĩnh các loại ô (0: Hư vô, 1: Bình thường, 2: Dễ vỡ, ...)
    - bridges: Danh sách các ô là cầu nối động (row, col)
    - bridge_indices: Ánh xạ từ tọa độ (row, col) sang chỉ số trong tuple bridge_state
    - initial_bridges: Trạng thái ban đầu của từng cầu nối (True = Mở, False = Đóng)
    - switches: Từ điển ánh xạ từ tọa độ công tắc (row, col) sang SwitchAction
    """
    rows: int
    cols: int
    start_pos: Tuple[int, int]
    goal_pos: Tuple[int, int]
    board: List[List[int]]
    bridges: List[Tuple[int, int]]
    bridge_indices: Dict[Tuple[int, int], int]
    initial_bridges: Tuple[bool, ...]
    switches: Dict[Tuple[int, int], SwitchAction]
    map_name: str = ""


def load_map_from_file(file_path: str) -> MapData:
    """
    Đọc file bản đồ Bloxorz (dạng file .txt chuẩn của đồ án):
    - Dòng 1: MAP_ROW MAP_COL start_col start_row
    - MAP_ROW dòng tiếp theo: Ma trận giá trị số các ô trên sàn
    - Các dòng còn lại (nếu có): Khai báo cơ chế công tắc và cầu liên kết (ManaBoa)
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Không tìm thấy file bản đồ: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if not lines:
        raise ValueError(f"File bản đồ rỗng: {file_path}")

    # Phân tích dòng 1
    first_parts = [int(x) for x in lines[0].split()]
    rows, cols = first_parts[0], first_parts[1]
    start_c, start_r = first_parts[2], first_parts[3]

    # Phân tích ma trận bản đồ
    board: List[List[int]] = []
    goal_pos: Optional[Tuple[int, int]] = None

    for r in range(rows):
        row_vals = [int(x) for x in lines[1 + r].split()]
        board.append(row_vals)
        for c in range(cols):
            if row_vals[c] == 9:
                goal_pos = (r, c)

    if goal_pos is None:
        raise ValueError(f"Bản đồ không chứa lỗ đích (giá trị 9): {file_path}")

    # Phân tích các dòng khai báo công tắc (ManaBoa)
    raw_switch_lines = lines[1 + rows:]
    switches: Dict[Tuple[int, int], SwitchAction] = {}
    all_bridges_set: Set[Tuple[int, int]] = set()

    for line in raw_switch_lines:
        parts = [int(x) for x in line.split()]
        if len(parts) < 2:
            continue
        sc, sr = parts[0], parts[1]
        tile_type = board[sr][sc]

        toggles: List[Tuple[int, int]] = []
        closes: List[Tuple[int, int]] = []
        opens: List[Tuple[int, int]] = []
        split_targets: Optional[Tuple[Tuple[int, int], Tuple[int, int]]] = None

        if tile_type == 7:
            # Công tắc phân thân: dạng `col row 2 r1 c1 r2 c2`
            split_targets = ((parts[3], parts[4]), (parts[5], parts[6]))

        elif tile_type in (4, 6, 8):
            # Công tắc chuyên đóng (4) hoặc chuyên mở (6, 8): dạng `col row count r1 c1 ...`
            cnt = parts[2]
            for i in range(cnt):
                br, bc = parts[3 + 2 * i], parts[4 + 2 * i]
                all_bridges_set.add((br, bc))
                if tile_type == 4:
                    closes.append((br, bc))
                else:
                    opens.append((br, bc))

        elif tile_type in (3, 5):
            # Công tắc đa chế độ (chữ X hoặc tròn đặc toggle/close/open)
            idx = 2
            num_tog = parts[idx]
            idx += 1
            for i in range(num_tog):
                br, bc = parts[idx + 2 * i], parts[idx + 2 * i + 1]
                all_bridges_set.add((br, bc))
                toggles.append((br, bc))
            idx += 2 * num_tog

            if idx < len(parts):
                num_close = parts[idx]
                idx += 1
                for i in range(num_close):
                    br, bc = parts[idx + 2 * i], parts[idx + 2 * i + 1]
                    all_bridges_set.add((br, bc))
                    closes.append((br, bc))
                idx += 2 * num_close

            if idx < len(parts):
                num_open = parts[idx]
                idx += 1
                for i in range(num_open):
                    br, bc = parts[idx + 2 * i], parts[idx + 2 * i + 1]
                    all_bridges_set.add((br, bc))
                    opens.append((br, bc))
                idx += 2 * num_open

        switches[(sr, sc)] = SwitchAction(
            tile_type=tile_type,
            toggle_bridges=toggles,
            close_bridges=closes,
            open_bridges=opens,
            split_targets=split_targets
        )

    # Đưa danh sách cầu về dạng danh sách có thứ tự cố định để tạo tuple trạng thái
    bridges_list = sorted(list(all_bridges_set))
    bridge_indices = {coord: idx for idx, coord in enumerate(bridges_list)}

    # Khởi tạo trạng thái ban đầu của từng cầu (True nếu trên map đang là ô sàn 1, False nếu đang là 0)
    initial_bridges_list = []
    for br, bc in bridges_list:
        is_open = (board[br][bc] != 0)
        initial_bridges_list.append(is_open)
    initial_bridges = tuple(initial_bridges_list)

    map_name = os.path.splitext(os.path.basename(file_path))[0]

    return MapData(
        rows=rows,
        cols=cols,
        start_pos=(start_r, start_c),
        goal_pos=goal_pos,
        board=board,
        bridges=bridges_list,
        bridge_indices=bridge_indices,
        initial_bridges=initial_bridges,
        switches=switches,
        map_name=map_name
    )
