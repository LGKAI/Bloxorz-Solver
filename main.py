"""
File: main.py
Mô tả: Điểm khởi chạy chính của đồ án Bloxorz Solver (Introduction to AI - Project 1).
      - Mặc định: Chạy giao diện đồ họa Pygame GUI trực quan, đầy đủ tính năng:
        `python main.py`
      - Hỗ trợ chạy dòng lệnh CLI (tương thích tuyệt đối với cú pháp yêu cầu của đồ án):
        `python main.py <màn_chơi> <thuật_toán>`
        Ví dụ:
        `python main.py 01 BFS`
        `python main.py 02 DFS`
        `python main.py 04 UCS`
        `python main.py 08 A*`
"""

import sys
import os

# Thiết lập mã hóa UTF-8 cho terminal Windows để hiển thị tiếng Việt rõ ràng
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Đưa thư mục Source vào sys.path để import dễ dàng
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from src.core import load_map_from_file, GameState, BlockState, Orientation
from src.solvers import (
    solve_bfs,
    solve_dfs,
    solve_ids,
    solve_ucs,
    solve_astar
)


def print_cli_board(game_state: GameState):
    """In bản đồ dạng ký tự trực quan trên giao diện dòng lệnh."""
    board = game_state.map_data.board
    rows = game_state.map_data.rows
    cols = game_state.map_data.cols
    occupied = set(game_state.block.occupied_cells())

    for r in range(rows):
        line = "  "
        for c in range(cols):
            if (r, c) in occupied:
                line += "X "
            elif (r, c) in game_state.map_data.bridge_indices:
                idx = game_state.map_data.bridge_indices[(r, c)]
                is_open = game_state.bridge_state[idx]
                line += "= " if is_open else ". "
            elif board[r][c] == 0:
                line += "  "
            else:
                line += f"{board[r][c]} "
        print(line)


def run_cli_solver(stage_str: str, algo_str: str):
    """Chạy giải thuật toán trên Terminal."""
    # Định dạng tên file bản đồ (hỗ trợ "01", "1", "map01", "map01.txt")
    if stage_str.endswith(".txt"):
        map_filename = stage_str
    elif stage_str.startswith("map"):
        map_filename = f"{stage_str}.txt"
    else:
        num = int(stage_str)
        map_filename = f"map{num:02d}.txt"

    # Tìm đường dẫn file bản đồ
    possible_paths = [
        os.path.join(CURRENT_DIR, "levels", map_filename),
        os.path.join(CURRENT_DIR, "..", "Reference", "map", map_filename),
        os.path.join(CURRENT_DIR, "map", map_filename),
        map_filename
    ]

    map_path = None
    for p in possible_paths:
        if os.path.exists(p):
            map_path = p
            break

    if not map_path:
        print(f"[LỖI] Không tìm thấy file bản đồ cho màn: {stage_str}")
        return

    map_data = load_map_from_file(map_path)
    init_block = BlockState(
        Orientation.STANDING,
        map_data.start_pos[0],
        map_data.start_pos[1]
    )
    start_state = GameState(init_block, map_data.initial_bridges, map_data)

    print("\n=======================================================")
    print(f" BẮT ĐẦU GIẢI: {map_data.map_name.upper()} | THUẬT TOÁN: {algo_str.upper()}")
    print("=======================================================")
    print(f"Kích thước sàn: {map_data.rows} hàng x {map_data.cols} cột")
    print(f"Vị trí bắt đầu: ({map_data.start_pos[0]}, {map_data.start_pos[1]})")
    print(f"Vị trí đích: ({map_data.goal_pos[0]}, {map_data.goal_pos[1]})")
    print(f"Số lượng cầu nối động: {len(map_data.bridges)}")
    print(f"Số lượng công tắc: {len(map_data.switches)}")
    print("\nBản đồ ban đầu:")
    print_cli_board(start_state)
    print("-------------------------------------------------------")

    algo_upper = algo_str.upper().replace("-", "").replace("_", "")

    result = None
    if algo_upper == "BFS":
        result = solve_bfs(start_state)
    elif algo_upper == "DFS":
        result = solve_dfs(start_state)
    elif algo_upper == "IDS":
        result = solve_ids(start_state)
    elif algo_upper == "UCS":
        result = solve_ucs(start_state, weighted=True)
    elif algo_upper in ("A*", "ASTAR", "BEST"):
        result = solve_astar(start_state, heuristic_type="relaxed_grid", weighted=True)
    else:
        print(f"[LỖI] Thuật toán không hợp lệ: {algo_str}")
        print("Các thuật toán hợp lệ: BFS, DFS, IDS, UCS, A* (hoặc BEST)")
        return

    print("\n" + result.summary())

    if result.success:
        print("ĐƯỜNG ĐI CHI TIẾT (SUCCESS ROAD):")
        print("=======================================================")
        for idx, (action, state) in enumerate(zip(["START"] + result.actions, result.states)):
            act_name = action.value if hasattr(action, "value") else str(action)
            print(f"\nBước {idx}: [{act_name}] -> {state.block}")
            print_cli_board(state)
        print("\n=======================================================")
        print(f"HOÀN THÀNH VỚI {result.solution_length} BƯỚC ĐI!")
    else:
        print("KHÔNG TÌM THẤY LỜI GIẢI!")


def main():
    """Hàm main: phân luồng GUI hoặc CLI dựa trên đối số truyền vào."""
    args = sys.argv[1:]

    # Nếu truyền đối số: chạy chế độ dòng lệnh CLI
    if len(args) >= 2:
        stage_arg = args[0]
        algo_arg = args[1]
        run_cli_solver(stage_arg, algo_arg)
    elif len(args) == 1 and args[0] in ("-h", "--help", "help"):
        print("CÁCH SỬ DỤNG:")
        print("  1. Khởi chạy giao diện đồ họa (GUI):")
        print("     python main.py")
        print("  2. Khởi chạy dòng lệnh (CLI):")
        print("     python main.py <màn_chơi> <thuật_toán>")
        print("     Ví dụ: python main.py 01 BFS")
        print("            python main.py 08 A*")
        print("     Thuật toán: BFS, DFS, IDS, UCS, A*")
    else:
        # Mặc định mở giao diện đồ họa GUI Pygame
        from src.gui.app import BloxorzApp
        levels_dir = os.path.join(CURRENT_DIR, "levels")
        app = BloxorzApp(levels_dir=levels_dir)
        app.run()


if __name__ == "__main__":
    main()
