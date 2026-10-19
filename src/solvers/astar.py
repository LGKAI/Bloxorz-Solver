"""
Module: astar.py
Mô tả: Thuật toán tìm kiếm A* (A-Star Search) cho game Bloxorz với các hàm Heuristic
      thông minh, đảm bảo tính chấp nhận được (Admissible) và nhất quán (Consistent).
      
      Thiết kế Heuristic:
      1. Relaxed Grid Distance (Khoảng cách lưới rút gọn qua BFS ngược):
         - Bỏ qua các ràng buộc xoay lật và xem toàn bộ sàn là đồ thị 4 hướng kết nối.
         - Tính khoảng cách bước đi ngắn nhất từ mọi ô (r, c) tới lỗ đích (goal_pos).
         - Vì mỗi bước lăn khối có thể dịch chuyển tọa độ tối đa 2 ô, nên h1(s) = ceil(dist / 2).
      2. Orientation Penalty (Phạt hướng lật):
         - Để chiến thắng, khối bắt buộc phải ở trạng thái ĐỨNG (STANDING) trên ô đích.
         - Nếu khối đang nằm ngang/dọc đè qua ô đích (khoảng cách = 0), nó bắt buộc phải lăn ra
           chỗ khác rồi mới dựng đứng quay lại được -> tốn ít nhất 2 bước phụ (h = 2).
         - Nếu khối đang nằm ở khoảng cách > 0, nó cần ít nhất max(1, ceil(dist / 2)) bước.
      3. Trường hợp phân thân (SPLIT):
         - Hai khối 1x1x1 cần di chuyển lại gần nhau để sáp nhập, sau đó tiến về đích:
           h(s) = ceil((dist_cube0 + dist_cube1) / 2).
      
      Chứng minh tính Admissible và Consistent:
      - Trong một bước di chuyển bất kỳ, tọa độ gần đích nhất của khối thay đổi tối đa 2 đơn vị lưới.
      - Do đó ceil(dist / 2) giảm tối đa 1 đơn vị sau mỗi bước.
      - Vì chi phí bước đi nhỏ nhất c(s, a, s') >= 1.0, ta luôn có:
        h(s) - h(s') <= 1.0 <= c(s, a, s') <=> h(s) <= c(s, a, s') + h(s').
      - Do đó Heuristic là Monotonically Consistent và Admissible, bảo đảm A* tìm ra lời giải tối ưu.
"""

import time
import tracemalloc
import heapq
import math
from collections import deque
from typing import Optional, List, Tuple, Dict
from src.core.block import Orientation
from src.core.game_state import GameState
from src.core.map_loader import MapData
from src.solvers.base_solver import SearchResult


def precompute_relaxed_grid_distances(map_data: MapData) -> Dict[Tuple[int, int], int]:
    """
    Tính trước khoảng cách bước đi ngắn nhất trên lưới 4 hướng từ mọi ô hợp lệ tới đích (BFS ngược).
    Chạy 1 lần duy nhất khi bắt đầu giải bản đồ (thời gian < 0.1 ms).
    """
    rows, cols = map_data.rows, map_data.cols
    goal_r, goal_c = map_data.goal_pos

    # Tập hợp các ô có thể đi lại được trên bản đồ (sàn thông thường, ô cam, và tất cả ô cầu)
    bridge_set = set(map_data.bridges)

    def is_tile_walkable(r: int, c: int) -> bool:
        if not (0 <= r < rows and 0 <= c < cols):
            return False
        if (r, c) in bridge_set:
            return True
        return map_data.board[r][c] != 0

    # Công tắc phân thân dịch chuyển khối tới vị trí xa chỉ trong 1 bước.
    # Để heuristic KHÔNG ước lượng quá, ta coi ô công tắc và 2 ô đích dịch chuyển
    # được nối với nhau bằng cạnh có độ dài 0 (hai chiều) trong đồ thị rút gọn.
    teleport_edges: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
    for sw_pos, sw in map_data.switches.items():
        if sw.split_targets:
            for tgt in sw.split_targets:
                teleport_edges.setdefault(sw_pos, []).append(tuple(tgt))
                teleport_edges.setdefault(tuple(tgt), []).append(sw_pos)

    # BFS 0-1 ngược từ ô đích: cạnh lưới có trọng số 1, cạnh teleport có trọng số 0
    distances: Dict[Tuple[int, int], int] = {(goal_r, goal_c): 0}
    dq = deque([(goal_r, goal_c)])
    while dq:
        cur = dq.popleft()
        cur_d = distances[cur]

        for nxt in teleport_edges.get(cur, []):
            if is_tile_walkable(nxt[0], nxt[1]) and distances.get(nxt, float("inf")) > cur_d:
                distances[nxt] = cur_d
                dq.appendleft(nxt)

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cur[0] + dr, cur[1] + dc
            if is_tile_walkable(nr, nc) and distances.get((nr, nc), float("inf")) > cur_d + 1:
                distances[(nr, nc)] = cur_d + 1
                dq.append((nr, nc))

    return distances


def calculate_heuristic(
    state: GameState,
    grid_distances: Dict[Tuple[int, int], int],
    heuristic_type: str = "relaxed_grid"
) -> float:
    """
    Tính giá trị ước lượng h(s) từ trạng thái hiện tại tới trạng thái đích.
    Hỗ trợ hai chế độ:
    - 'relaxed_grid': Sử dụng khoảng cách lưới ngắn nhất (tối ưu và thông tin nhất).
    - 'manhattan': Sử dụng khoảng cách Manhattan chuẩn.
    """
    goal_r, goal_c = state.map_data.goal_pos
    block = state.block
    ori = block.orientation

    def get_dist(r: int, c: int) -> float:
        if heuristic_type == "relaxed_grid":
            # Ô không nối được tới đích trong đồ thị rút gọn -> trả về 0 (luôn an toàn, không ước lượng quá)
            return grid_distances.get((r, c), 0)
        # Chế độ 'manhattan': chỉ dùng để so sánh, KHÔNG đảm bảo admissible khi màn có công tắc phân thân
        return abs(r - goal_r) + abs(c - goal_c)

    if ori == Orientation.STANDING:
        d = get_dist(block.r, block.c)
        return math.ceil(d / 2.0)

    elif ori in (Orientation.HORIZONTAL, Orientation.VERTICAL):
        cells = block.occupied_cells()
        d0 = get_dist(cells[0][0], cells[0][1])
        d1 = get_dist(cells[1][0], cells[1][1])
        min_d = min(d0, d1)

        # Nếu một nửa khối đang nằm đè lên CHÍNH Ô ĐÍCH:
        # Khối không thể thắng khi nằm, bắt buộc phải lăn ra ngoài rồi lăn vào để đứng -> tốn ít nhất 2 bước.
        if (goal_r, goal_c) in cells:
            return 2.0

        return max(1.0, math.ceil(min_d / 2.0))

    elif ori == Orientation.SPLIT:
        d0 = get_dist(block.r, block.c)
        d1 = get_dist(block.r1, block.c1)
        # Cả 2 khối đều phải di chuyển để hội tụ và đưa khối về đích
        return max(1.0, math.ceil((d0 + d1) / 2.0))

    return 0.0


def solve_astar(
    start_state: GameState,
    heuristic_type: str = "relaxed_grid",
    weighted: bool = False
) -> SearchResult:
    """
    Giải bài toán Bloxorz bằng thuật toán tìm kiếm A*.
    - heuristic_type: 'relaxed_grid' hoặc 'manhattan'.
    - weighted: Nếu True, kết hợp với chi phí bước đi của UCS (Fragile penalty, Standing penalty).
                Nếu False, tính số bước đi tối thiểu (mỗi bước = 1.0).
    """
    tracemalloc.start()
    start_time = time.perf_counter()

    expanded_nodes = 0
    generated_nodes = 1

    # Tính trước khoảng cách lưới
    grid_distances = precompute_relaxed_grid_distances(start_state.map_data)

    if start_state.is_goal():
        elapsed = time.perf_counter() - start_time
        peak_mem = tracemalloc.get_traced_memory()[1] / 1024.0
        tracemalloc.stop()
        return SearchResult(
            success=True,
            algorithm="A*",
            actions=[],
            states=[start_state],
            search_time=elapsed,
            peak_memory_kb=peak_mem,
            expanded_nodes=0,
            generated_nodes=1,
            solution_length=0,
            solution_cost=0.0
        )

    # Frontier chứa tuple: (f_cost, g_cost, count, state, actions)
    # f(n) = g(n) + h(n)
    entry_count = 0
    h_start = calculate_heuristic(start_state, grid_distances, heuristic_type)
    frontier = []
    heapq.heappush(frontier, (h_start, 0.0, entry_count, start_state, []))

    # Bảng lưu g_cost nhỏ nhất từng đạt được tới mỗi trạng thái
    best_g = {start_state.canonical_key(): 0.0}

    found_actions: Optional[List] = None
    final_cost = 0.0

    while frontier:
        f, g, _, current_state, actions = heapq.heappop(frontier)

        # Bỏ qua nút lỗi thời nếu đã tìm được đường đến trạng thái này với g_cost thấp hơn
        if g > best_g.get(current_state.canonical_key(), float("inf")):
            continue

        expanded_nodes += 1

        # Kiểm tra đích khi LẤY RA khỏi Frontier (đảm bảo tính tối ưu của A*)
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

            if new_g < best_g.get(key, float("inf")):
                best_g[key] = new_g
                h = calculate_heuristic(next_state, grid_distances, heuristic_type)
                new_f = new_g + h
                entry_count += 1
                heapq.heappush(frontier, (new_f, new_g, entry_count, next_state, actions + [action]))

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
            algorithm="A*",
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
        algorithm="A*",
        actions=[],
        states=[],
        search_time=elapsed,
        peak_memory_kb=peak_mem,
        expanded_nodes=expanded_nodes,
        generated_nodes=generated_nodes,
        solution_length=0,
        solution_cost=0.0
    )
