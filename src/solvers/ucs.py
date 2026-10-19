"""
Module: ucs.py
Mô tả: Thuật toán tìm kiếm chi phí đều (Uniform-Cost Search - UCS) cho game Bloxorz.
      Đặc tính:
      - Sử dụng hàng đợi ưu tiên Priority Queue (heapq) sắp xếp theo tổng chi phí g(n).
      - Hàm chi phí phi đồng nhất (non-uniform cost function) được thiết kế có ý nghĩa thực tế:
        + Bước di chuyển tiêu chuẩn: cost = 1.0
        + Lăn qua/lên ô cam dễ vỡ (Fragile tile): cost = 2.0 (phạt rủi ro do nguy cơ sập sàn)
        + Dựng đứng khối (từ nằm sang đứng): cost = 1.2 (tiêu tốn năng lượng nâng trọng tâm)
      - Đảm bảo tìm được đường đi có tổng chi phí nhỏ nhất (Cost-Optimal).
      - Kiểm tra đích khi LẤY RA khỏi Frontier (Goal test on expansion) để đảm bảo tính tối ưu.
"""

import time
import tracemalloc
import heapq
from typing import Optional, List, Tuple
from src.core.game_state import GameState
from src.solvers.base_solver import SearchResult


def solve_ucs(start_state: GameState, weighted: bool = True) -> SearchResult:
    """
    Giải bài toán Bloxorz bằng thuật toán UCS.
    - weighted: Nếu True, áp dụng hàm chi phí phi đồng nhất (Fragile penalty, Standing penalty).
                Nếu False, mỗi bước đi có cost = 1.0 (tương đương BFS có trọng số đều).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    generated_nodes = 1

    # Kiểm tra nếu đã ở đích ngay từ đầu
    if start_state.is_goal():
        elapsed = time.perf_counter() - start_time
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
        tracemalloc.stop()
        return SearchResult(
            success=True,
            algorithm="UCS",
            actions=[],
            states=[start_state],
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=0,
            generated_nodes=1,
            solution_length=0,
            solution_cost=0.0
        )

    # Priority queue chứa: (g_cost, count, state, actions)
    # count đóng vai trò tie-breaker tránh so sánh trực tiếp đối tượng GameState
    entry_count = 0
    frontier = []
    heapq.heappush(frontier, (0.0, entry_count, start_state, []))

    # Bảng lưu chi phí tốt nhất từng tìm thấy đến mỗi trạng thái
    best_cost = {start_state.canonical_key(): 0.0}

    found_actions: Optional[List] = None
    final_cost = 0.0

    while frontier:
        g, _, current_state, actions = heapq.heappop(frontier)

        # Bỏ qua nếu đã tìm thấy đường đi khác tới trạng thái này với chi phí thấp hơn
        if g > best_cost.get(current_state.canonical_key(), float("inf")):
            continue

        expanded_nodes += 1

        # Đạt đích khi LẤY RA khỏi Frontier -> đảm bảo lời giải là tối ưu nhất về chi phí
        if current_state.is_goal():
            found_actions = actions
            final_cost = g
            break

        for action in current_state.get_valid_actions():
            next_state = current_state.transition(action)
            if next_state is None:
                continue

            generated_nodes += 1
            step_c = current_state.calculate_step_cost(next_state) if weighted else 1.0
            new_g = g + step_c
            key = next_state.canonical_key()

            if new_g < best_cost.get(key, float("inf")):
                best_cost[key] = new_g
                entry_count += 1
                heapq.heappush(frontier, (new_g, entry_count, next_state, actions + [action]))

    elapsed = time.perf_counter() - start_time
    peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
    tracemalloc.stop()

    if found_actions is not None:
        states = [start_state]
        curr = start_state
        for act in found_actions:
            nxt = curr.transition(act)
            if nxt is not None:
                states.append(nxt)
                curr = nxt

        return SearchResult(
            success=True,
            algorithm="UCS",
            actions=found_actions,
            states=states,
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            solution_length=len(found_actions),
            solution_cost=final_cost
        )

    return SearchResult(
        success=False,
        algorithm="UCS",
        actions=[],
        states=[],
        search_time=elapsed,
        peak_memory_kb=peak_mem,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        solution_length=0,
        solution_cost=0.0
    )
