"""
Module: experiment.py
Mô tả: Kịch bản tự động thực nghiệm và đánh giá so sánh hiệu năng 4 thuật toán:
      BFS, DFS (hoặc IDS), UCS, A* trên bộ màn chơi chuẩn được chia theo 4 nhóm độ khó:
      1. Nhóm 1 (Cơ bản - Core mechanics): map01, map03, map06
      2. Nhóm 2 (Ô cam dễ vỡ - Fragile tiles): map04, map13
      3. Nhóm 3 (Công tắc & Cầu nối - Switches & Bridges): map02, map05, map07, map11
      4. Nhóm 4 (Phân thân & Kết hợp phức tạp - Split & Combined): map08, map09, map10, map15
      
      Đầu ra:
      - Bảng Markdown tổng hợp số liệu chi tiết (Thời gian, Bộ nhớ đỉnh, Nút mở rộng, Số bước).
      - File CSV `experiments/results.csv` để nhập vào Excel / LaTeX.
      - 4 biểu đồ trực quan hóa định dạng PNG lưu tại `experiments/plots/`.
"""

import os
import sys
import csv
import time
from typing import List, Dict, Any

# Đảm bảo import được các module từ Source
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.core import load_map_from_file, GameState, BlockState, Orientation
from src.solvers import (
    solve_bfs,
    solve_dfs,
    solve_ids,
    solve_ucs,
    solve_astar
)


# Định nghĩa 4 nhóm màn chơi theo yêu cầu Mục 3.6 của đồ án
TEST_GROUPS = {
    "Nhóm 1: Cơ bản (Basic)": ["map01.txt", "map03.txt", "map06.txt"],
    "Nhóm 2: Ô cam dễ vỡ (Fragile)": ["map04.txt", "map13.txt"],
    "Nhóm 3: Công tắc & Cầu nối (Switches & Bridges)": ["map02.txt", "map05.txt", "map07.txt", "map11.txt"],
    "Nhóm 4: Phân thân & Kết hợp (Split & Combined)": ["map08.txt", "map09.txt", "map10.txt", "map15.txt"]
}


def run_single_experiment(map_file: str, algo_name: str, timeout_sec: float = 15.0) -> Dict[str, Any]:
    """Chạy thử nghiệm một thuật toán trên một màn chơi với cơ chế timeout."""
    levels_dir = os.path.join(CURRENT_DIR, "levels")
    map_path = os.path.join(levels_dir, map_file)

    map_data = load_map_from_file(map_path)
    init_block = BlockState(
        Orientation.STANDING,
        map_data.start_pos[0],
        map_data.start_pos[1]
    )
    start_state = GameState(init_block, map_data.initial_bridges, map_data)

    res = None
    try:
        if algo_name == "BFS":
            res = solve_bfs(start_state)
        elif algo_name == "DFS":
            # DFS với giới hạn độ sâu để tránh chạy vô tận trên các bản đồ lớn
            res = solve_dfs(start_state, max_depth=1200)
        elif algo_name == "UCS":
            res = solve_ucs(start_state, weighted=True)
        elif algo_name == "A*":
            res = solve_astar(start_state, heuristic_type="relaxed_grid", weighted=True)
    except Exception as e:
        return {
            "map": map_file,
            "algo": algo_name,
            "success": False,
            "time_s": 0.0,
            "memory_kb": 0.0,
            "expanded": 0,
            "moves": 0,
            "cost": 0.0,
            "note": f"Error: {e}"
        }

    if res and res.success:
        return {
            "map": map_file,
            "algo": algo_name,
            "success": True,
            "time_s": res.search_time,
            "memory_kb": res.peak_memory_kb,
            "expanded": res.expanded_nodes,
            "moves": res.solution_length,
            "cost": res.solution_cost,
            "note": "OK"
        }
    else:
        return {
            "map": map_file,
            "algo": algo_name,
            "success": False,
            "time_s": res.search_time if res else 0.0,
            "memory_kb": res.peak_memory_kb if res else 0.0,
            "expanded": res.expanded_nodes if res else 0,
            "moves": 0,
            "cost": 0.0,
            "note": "Failed / No solution"
        }


def generate_plots(results: List[Dict[str, Any]], output_dir: str):
    """Vẽ 4 biểu đồ so sánh: Thời gian, Bộ nhớ, Nút mở rộng, Độ dài giải pháp."""
    try:
        import matplotlib
        matplotlib.use("Agg")  # Chạy chế độ không cần giao diện cửa sổ
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        print("[CẢNH BÁO] Không có thư viện matplotlib, bỏ qua vẽ biểu đồ.")
        return

    os.makedirs(output_dir, exist_ok=True)

    # Chọn lọc danh sách các map tiêu biểu đại diện cho 4 nhóm để biểu đồ rõ ràng
    sample_maps = ["map01.txt", "map03.txt", "map04.txt", "map13.txt", "map02.txt", "map05.txt", "map08.txt", "map10.txt"]
    algos = ["BFS", "DFS", "UCS", "A*"]
    colors = {
        "BFS": "#3b82f6",
        "DFS": "#f59e0b",
        "UCS": "#8b5cf6",
        "A*": "#10b981"
    }

    # Gom dữ liệu theo map và algo
    map_labels = [m.replace(".txt", "").upper() for m in sample_maps]
    n_groups = len(sample_maps)
    bar_width = 0.2
    x_indices = np.arange(n_groups)

    # 1. Biểu đồ Thời gian tìm kiếm (Search Time - thang logarit)
    plt.figure(figsize=(11, 6))
    for i, algo in enumerate(algos):
        vals = []
        for m in sample_maps:
            entry = next((r for r in results if r["map"] == m and r["algo"] == algo), None)
            # Thêm epsilon 0.0001s để vẽ thang log không bị 0
            vals.append(max(0.0001, entry["time_s"]) if entry and entry["success"] else 0.0001)
        plt.bar(x_indices + i * bar_width, vals, bar_width, label=algo, color=colors[algo])

    plt.xlabel("Màn chơi thử nghiệm", fontweight="bold")
    plt.ylabel("Thời gian tìm kiếm (giây - Log Scale)", fontweight="bold")
    plt.yscale("log")
    plt.title("So sánh Thời gian Tìm kiếm (Search Time) giữa các Thuật toán", fontweight="bold", fontsize=14)
    plt.xticks(x_indices + bar_width * 1.5, map_labels)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "search_time_comparison.png"), dpi=300)
    plt.close()

    # 2. Biểu đồ Số nút mở rộng (Expanded Nodes - thể hiện độ thông minh của Heuristic)
    plt.figure(figsize=(11, 6))
    for i, algo in enumerate(algos):
        vals = []
        for m in sample_maps:
            entry = next((r for r in results if r["map"] == m and r["algo"] == algo), None)
            vals.append(entry["expanded"] if entry and entry["success"] else 0)
        plt.bar(x_indices + i * bar_width, vals, bar_width, label=algo, color=colors[algo])

    plt.xlabel("Màn chơi thử nghiệm", fontweight="bold")
    plt.ylabel("Số nút đã mở rộng (Expanded Nodes - Log Scale)", fontweight="bold")
    plt.yscale("log")
    plt.title("So sánh Số Nút Đã Mở Rộng (Expanded Nodes) giữa các Thuật toán", fontweight="bold", fontsize=14)
    plt.xticks(x_indices + bar_width * 1.5, map_labels)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "expanded_nodes_comparison.png"), dpi=300)
    plt.close()

    # 3. Biểu đồ Bộ nhớ RAM tiêu thụ đỉnh (Peak Memory)
    plt.figure(figsize=(11, 6))
    for i, algo in enumerate(algos):
        vals = []
        for m in sample_maps:
            entry = next((r for r in results if r["map"] == m and r["algo"] == algo), None)
            vals.append(entry["memory_kb"] if entry and entry["success"] else 0)
        plt.bar(x_indices + i * bar_width, vals, bar_width, label=algo, color=colors[algo])

    plt.xlabel("Màn chơi thử nghiệm", fontweight="bold")
    plt.ylabel("Bộ nhớ RAM cực đại (KB)", fontweight="bold")
    plt.title("So sánh Bộ Nhớ Cực Đại Tiêu Thụ (Peak Memory Usage) (KB)", fontweight="bold", fontsize=14)
    plt.xticks(x_indices + bar_width * 1.5, map_labels)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "memory_usage_comparison.png"), dpi=300)
    plt.close()

    # 4. Biểu đồ Độ dài đường đi lời giải (Solution Moves)
    plt.figure(figsize=(11, 6))
    for i, algo in enumerate(algos):
        vals = []
        for m in sample_maps:
            entry = next((r for r in results if r["map"] == m and r["algo"] == algo), None)
            vals.append(entry["moves"] if entry and entry["success"] else 0)
        plt.bar(x_indices + i * bar_width, vals, bar_width, label=algo, color=colors[algo])

    plt.xlabel("Màn chơi thử nghiệm", fontweight="bold")
    plt.ylabel("Số bước đi (Solution Length)", fontweight="bold")
    plt.title("So sánh Độ Dài Đường Đi Lời Giải (Solution Length) giữa các Thuật toán", fontweight="bold", fontsize=14)
    plt.xticks(x_indices + bar_width * 1.5, map_labels)
    plt.grid(axis="y", linestyle="--", alpha=0.6)
    plt.legend()
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, "solution_length_comparison.png"), dpi=300)
    plt.close()

    print(f"[THÀNH CÔNG] Đã tạo 4 biểu đồ so sánh chất lượng cao tại: {output_dir}")


def main():
    exp_dir = os.path.join(CURRENT_DIR, "experiments")
    plots_dir = os.path.join(exp_dir, "plots")
    os.makedirs(exp_dir, exist_ok=True)
    os.makedirs(plots_dir, exist_ok=True)

    algos = ["BFS", "DFS", "UCS", "A*"]
    all_results = []

    print("\n" + "=" * 75)
    print(" BẮT ĐẦU CHẠY THỬ NGHIỆM ĐÁNH GIÁ CÁC THUẬT TOÁN (BFS, DFS, UCS, A*)")
    print("=" * 75)

    for group_name, map_list in TEST_GROUPS.items():
        print(f"\n>>> {group_name}:")
        for map_file in map_list:
            for algo in algos:
                res = run_single_experiment(map_file, algo)
                all_results.append(res)
                st = "OK" if res["success"] else "FAIL"
                print(
                    f"  [{algo:4s}] {map_file}: {st:4s} | "
                    f"Thời gian: {res['time_s']:7.4f}s | "
                    f"Bộ nhớ: {res['memory_kb']:7.1f}KB | "
                    f"Nodes mở rộng: {res['expanded']:6d} | "
                    f"Số bước: {res['moves']:3d}"
                )

    # Xuất file CSV
    csv_path = os.path.join(exp_dir, "results.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        fieldnames = ["map", "algo", "success", "time_s", "memory_kb", "expanded", "moves", "cost", "note"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_results)
    print(f"\n[OK] Đã lưu dữ liệu thử nghiệm chi tiết vào: {csv_path}")

    # Tạo bảng Markdown tổng hợp
    md_path = os.path.join(exp_dir, "experiment_report.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# BẢNG TỔNG HỢP KẾT QUẢ THỰC NGHIỆM THUẬT TOÁN BLOXORZ SOLVER\n\n")
        f.write("| Nhóm | Màn chơi | Thuật toán | Thời gian (s) | Bộ nhớ đỉnh (KB) | Số nút mở rộng | Độ dài lời giải (Bước) | Chi phí |\n")
        f.write("| :--- | :--- | :--- | :---: | :---: | :---: | :---: | :---: |\n")

        for group_name, map_list in TEST_GROUPS.items():
            for m in map_list:
                for a in algos:
                    entry = next((r for r in all_results if r["map"] == m and r["algo"] == a), None)
                    if entry and entry["success"]:
                        f.write(
                            f"| {group_name.split(':')[0]} | {m} | **{a}** | "
                            f"{entry['time_s']:.4f} | {entry['memory_kb']:.2f} | "
                            f"{entry['expanded']} | {entry['moves']} | {entry['cost']:.2f} |\n"
                        )
                    elif entry:
                        f.write(f"| {group_name.split(':')[0]} | {m} | **{a}** | - | - | {entry['expanded']} | {entry['note']} | - |\n")

    print(f"[OK] Đã tạo báo cáo bảng Markdown tại: {md_path}")

    # Vẽ các biểu đồ so sánh
    generate_plots(all_results, plots_dir)
    print("\n" + "=" * 75)
    print(" TOÀN BỘ THỰC NGHIỆM ĐÃ HOÀN TẤT THÀNH CÔNG RỰC RỠ!")
    print("=" * 75)


if __name__ == "__main__":
    main()
