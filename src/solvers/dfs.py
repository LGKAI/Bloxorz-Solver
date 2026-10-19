"""
Module: dfs.py
Mô tả: Thuật toán tìm kiếm theo chiều sâu (Depth-First Search - DFS)
      và Tìm kiếm sâu dần (Iterative Deepening Search - IDS) cho game Bloxorz.
      Đặc tính:
      - Sử dụng cấu trúc ngăn xếp LIFO (Stack).
      - Xử lý trạng thái lặp và chu trình bằng tập Visited Set để tránh lặp vô tận.
      - Hỗ trợ cả DFS chuẩn (với visited set) và IDS (đảm bảo độ dài tối ưu với bộ nhớ O(b*d)).
"""

import time
import tracemalloc
from typing import Optional, List, Tuple
from src.core.game_state import GameState
from src.solvers.base_solver import SearchResult


def solve_dfs(start_state: GameState, max_depth: Optional[int] = 1000) -> SearchResult:
    """
    Giải bài toán Bloxorz bằng thuật toán DFS (sử dụng ngăn xếp Stack và Visited Set).
    - Tránh lặp vô tận nhờ kiểm tra trạng thái trong visited.
    - Giới hạn max_depth để đảm bảo không đào sâu quá mức trong không gian trạng thái lớn.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    generated_nodes = 1

    if start_state.is_goal():
        elapsed = time.perf_counter() - start_time
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
        tracemalloc.stop()
        return SearchResult(
            success=True,
            algorithm="DFS",
            actions=[],
            states=[start_state],
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=0,
            generated_nodes=1,
            solution_length=0,
            solution_cost=0.0
        )

    # Stack lưu trữ: (trạng thái hiện tại, danh sách hành động, độ sâu hiện tại)
    stack = [(start_state, [], 0)]
    visited = {start_state.canonical_key()}

    found_actions: Optional[List] = None

    while stack:
        current_state, actions, depth = stack.pop()
        expanded_nodes += 1

        if current_state.is_goal():
            found_actions = actions
            break

        if max_depth is not None and depth >= max_depth:
            continue

        # Duyệt qua các hướng đi hợp lệ (đảo ngược để thứ tự duyệt giống thứ tự tự nhiên khi pop)
        for action in reversed(current_state.get_valid_actions()):
            next_state = current_state.transition(action)
            if next_state is None:
                continue

            generated_nodes += 1
            key = next_state.canonical_key()

            if key not in visited:
                visited.add(key)
                stack.append((next_state, actions + [action], depth + 1))

    elapsed = time.perf_counter() - start_time
    peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
    tracemalloc.stop()

    if found_actions is not None:
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
            algorithm="DFS",
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
        algorithm="DFS",
        actions=[],
        states=[],
        search_time=elapsed,
        peak_memory_kb=peak_mem,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        solution_length=0,
        solution_cost=0.0
    )


def solve_ids(start_state: GameState, max_depth_limit: int = 60) -> SearchResult:
    """
    Tìm kiếm sâu dần (Iterative Deepening Search - IDS):
    Lặp lại DFS với độ sâu tăng dần từ 0 đến max_depth_limit.
    Đảm bảo:
    - Tìm được lời giải tối ưu về số bước đi (như BFS).
    - Bộ nhớ cực kỳ tiết kiệm: O(d) tuyến tính theo độ sâu.
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    total_expanded = 0
    total_generated = 1

    if start_state.is_goal():
        elapsed = time.perf_counter() - start_time
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
        tracemalloc.stop()
        return SearchResult(
            success=True,
            algorithm="IDS",
            actions=[],
            states=[start_state],
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=0,
            generated_nodes=1,
            solution_length=0,
            solution_cost=0.0
        )

    found_actions: Optional[List] = None

    for depth_limit in range(1, max_depth_limit + 1):
        # Chạy Depth-Limited Search (DLS)
        stack = [(start_state, [], 0)]
        # Trong IDS, visited lưu theo đường đi hiện tại hoặc ghi nhận độ sâu nhỏ nhất đã đến
        visited_at_depth = {start_state.canonical_key(): 0}

        while stack:
            current_state, actions, d = stack.pop()
            total_expanded += 1

            if current_state.is_goal():
                found_actions = actions
                break

            if d >= depth_limit:
                continue

            for action in reversed(current_state.get_valid_actions()):
                next_state = current_state.transition(action)
                if next_state is None:
                    continue

                total_generated += 1
                key = next_state.canonical_key()

                # Chỉ duyệt nếu chưa từng tới hoặc tới ở độ sâu nhỏ hơn (tiết kiệm bước)
                if key not in visited_at_depth or d + 1 < visited_at_depth[key]:
                    visited_at_depth[key] = d + 1
                    stack.append((next_state, actions + [action], d + 1))

        if found_actions is not None:
            break

    elapsed = time.perf_counter() - start_time
    peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
    tracemalloc.stop()

    if found_actions is not None:
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
            algorithm="IDS",
            actions=found_actions,
            states=states,
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=total_expanded,
            generated_nodes=total_generated,
            solution_length=len(found_actions),
            solution_cost=total_cost
        )

    return SearchResult(
        success=False,
        algorithm="IDS",
        actions=[],
        states=[],
        search_time=elapsed,
        peak_memory_kb=peak_mem,
        expanded_nodes=total_expanded,
        generated_nodes=total_generated,
        solution_length=0,
        solution_cost=0.0
    )
