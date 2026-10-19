"""
Module: bfs.py
Mô tả: Thuật toán tìm kiếm theo chiều rộng (Breadth-First Search - BFS) cho Bloxorz.
      Đặc tính:
      - Sử dụng hàng đợi FIFO (Queue / collections.deque).
      - Đảm bảo tìm được lời giải tối ưu về số bước đi (ngắn nhất).
      - Sử dụng tập Visited Set với khóa băm trạng thái O(1) để loại bỏ chu trình và trạng thái lặp.
      - Đo lường chính xác thời gian (time.perf_counter) và bộ nhớ đỉnh (tracemalloc).
"""

import time
import tracemalloc
from collections import deque
from typing import Optional, List, Tuple
from src.core.game_state import GameState
from src.solvers.base_solver import SearchResult


def solve_bfs(start_state: GameState) -> SearchResult:
    """
    Giải bài toán Bloxorz bằng thuật toán BFS.
    Trả về đối tượng SearchResult chứa lời giải và các số liệu đo lường.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    generated_nodes = 1

    # Kiểm tra ngay nếu trạng thái đầu tiên đã là đích
    if start_state.is_goal():
        elapsed = time.perf_counter() - start_time
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
        tracemalloc.stop()
        return SearchResult(
            success=True,
            algorithm="BFS",
            actions=[],
            states=[start_state],
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=0,
            generated_nodes=1,
            solution_length=0,
            solution_cost=0.0
        )

    # Hàng đợi lưu trữ: tuple (trạng thái hiện tại, danh sách các hành động đã thực hiện)
    queue = deque([(start_state, [])])
    visited = {start_state.canonical_key()}

    found_actions: Optional[List] = None

    while queue:
        current_state, actions = queue.popleft()
        expanded_nodes += 1

        for action in current_state.get_valid_actions():
            next_state = current_state.transition(action)
            if next_state is None:
                continue

            generated_nodes += 1
            key = next_state.canonical_key()

            if key not in visited:
                new_actions = actions + [action]

                # Kiểm tra đích ngay khi sinh trạng thái (Goal Test on Generation)
                # Với BFS trên đồ thị không trọng số, điều này bảo toàn tính tối ưu 100%
                if next_state.is_goal():
                    found_actions = new_actions
                    break

                visited.add(key)
                queue.append((next_state, new_actions))

        if found_actions is not None:
            break

    elapsed = time.perf_counter() - start_time
    peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
    tracemalloc.stop()

    if found_actions is not None:
        # Tái hiện danh sách các trạng thái dọc theo đường đi lời giải
        states = [start_state]
        curr = start_state
        total_cost = 0.0
        for act in found_actions:
            nxt = curr.transition(act)
            if nxt is not None:
                total_cost += curr.calculate_step_cost(nxt)
                states.append(nxt)
                curr = nxt

        return SearchResult(
            success=True,
            algorithm="BFS",
            actions=found_actions,
            states=states,
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=expanded_nodes,
            generated_nodes=generated_nodes,
            solution_length=len(found_actions),
            solution_cost=total_cost
        )

    return SearchResult(
        success=False,
        algorithm="BFS",
        actions=[],
        states=[],
        search_time=elapsed,
        peak_memory_kb=peak_mem,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        solution_length=0,
        solution_cost=0.0
    )
