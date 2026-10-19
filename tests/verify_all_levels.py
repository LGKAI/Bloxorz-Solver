"""
Script kiểm chứng tự động (dùng cho báo cáo và để tự kiểm tra code):
  1. Chạy BFS, UCS, A* trên tất cả các màn trong thư mục levels/.
  2. Kiểm tra tính đúng đắn:
     - A* (đơn vị chi phí = 1/bước) phải cho đúng số bước như BFS (BFS tối ưu số bước).
     - A* (chi phí có trọng số) phải cho đúng tổng chi phí như UCS (UCS tối ưu chi phí).
     Nếu lệch => heuristic KHÔNG chấp nhận được (admissible) trên màn đó.
  3. Phát lại lời giải bằng cách mô phỏng độc lập để chắc chắn lời giải hợp lệ.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from src.core import load_map_from_file, GameState, BlockState, Orientation
from src.solvers import solve_bfs, solve_ucs, solve_astar


def make_state(path):
    m = load_map_from_file(path)
    b = BlockState(Orientation.STANDING, m.start_pos[0], m.start_pos[1])
    return GameState(b, m.initial_bridges, m)


def replay_ok(start, actions):
    """Mô phỏng lại chuỗi hành động từ đầu, trả về True nếu kết thúc ở đích."""
    s = start
    for a in actions:
        s = s.transition(a)
        if s is None:
            return False
    return s.is_goal()


def main(time_limit=60.0):
    levels = os.path.join(ROOT, "levels")
    files = sorted(f for f in os.listdir(levels) if f.endswith(".txt"))
    bad = 0
    for f in files:
        st = make_state(os.path.join(levels, f))
        t0 = time.time()
        bfs = solve_bfs(st)
        ucs = solve_ucs(st, weighted=True)
        a1 = solve_astar(st, weighted=False)
        a2 = solve_astar(st, weighted=True)
        dt = time.time() - t0

        issues = []
        if not bfs.success:
            issues.append("BFS không có lời giải")
        else:
            if not replay_ok(st, bfs.actions):
                issues.append("lời giải BFS không hợp lệ")
            if a1.success and a1.solution_length != bfs.solution_length:
                issues.append(f"A*(unit) {a1.solution_length} != BFS {bfs.solution_length}")
            if a2.success and abs(a2.solution_cost - ucs.solution_cost) > 1e-9:
                issues.append(f"A*(w) {a2.solution_cost:.2f} != UCS {ucs.solution_cost:.2f}")
            if not (a1.success and a2.success and ucs.success):
                issues.append("có solver thất bại")
        status = "OK " if not issues else "LỖI"
        if issues:
            bad += 1
        print(f"{status} {f}: BFS={bfs.solution_length if bfs.success else '-'} "
              f"UCSc={ucs.solution_cost:.1f} A*u={a1.solution_length} A*wc={a2.solution_cost:.1f} "
              f"exp(BFS/UCS/A*)={bfs.expanded_nodes}/{ucs.expanded_nodes}/{a2.expanded_nodes} "
              f"({dt:.1f}s) {'; '.join(issues)}", flush=True)
    print(f"\nTổng số màn lỗi: {bad}/{len(files)}")


if __name__ == "__main__":
    main()
