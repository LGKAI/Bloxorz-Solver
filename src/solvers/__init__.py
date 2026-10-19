from src.solvers.base_solver import SearchResult
from src.solvers.bfs import solve_bfs
from src.solvers.dfs import solve_dfs, solve_ids
from src.solvers.ucs import solve_ucs
from src.solvers.astar import solve_astar

__all__ = [
    "SearchResult",
    "solve_bfs",
    "solve_dfs",
    "solve_ids",
    "solve_ucs",
    "solve_astar"
]
