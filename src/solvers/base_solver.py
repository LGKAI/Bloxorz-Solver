"""
Module: base_solver.py
Mô tả: Định nghĩa lớp kết quả tìm kiếm (SearchResult) và giao diện cơ sở cho các thuật toán tìm kiếm.
      Ghi nhận đầy đủ 4 tiêu chí đánh giá theo yêu cầu đồ án:
      1. Thời gian tìm kiếm (Search Time)
      2. Bộ nhớ tiêu thụ cực đại (Memory Usage - Peak Memory)
      3. Số trạng thái đã mở rộng (Expanded Nodes)
      4. Độ dài đường đi lời giải (Solution Length / Moves)
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any
from src.core.game_state import GameState


@dataclass
class SearchResult:
    """
    Chứa kết quả và số liệu đo lường hiệu năng của thuật toán tìm kiếm:
    - success: Tìm thấy lời giải hay không
    - algorithm: Tên thuật toán (BFS, DFS, IDS, UCS, A*)
    - actions: Danh sách các hành động từ trạng thái đầu đến đích
    - states: Chuỗi các trạng thái (GameState) tương ứng theo từng bước
    - search_time: Thời gian tìm kiếm tính bằng giây (s)
    - peak_memory_kb: Bộ nhớ RAM cực đại tiêu thụ trong quá trình tìm kiếm (KB)
    - expanded_nodes: Số lượng nút đã được lấy ra khỏi Frontier để xét mở rộng
    - generated_nodes: Tổng số nút trạng thái con đã được sinh ra
    - solution_length: Số bước đi của giải pháp (bằng len(actions))
    - solution_cost: Tổng chi phí đường đi (hữu ích cho UCS và A*)
    """
    success: bool
    algorithm: str
    actions: List[Any] = field(default_factory=list)
    states: List[GameState] = field(default_factory=list)
    search_time: float = 0.0
    peak_memory_kb: float = 0.0
    expanded_nodes: int = 0
    generated_nodes: int = 0
    solution_length: int = 0
    solution_cost: float = 0.0

    def summary(self) -> str:
        """Trả về chuỗi tóm tắt kết quả đo lường."""
        status = "THÀNH CÔNG" if self.success else "THẤT BẠI / KHÔNG CÓ LỜI GIẢI"
        return (
            f"=== KẾT QUẢ TÌM KIẾM: {self.algorithm} ===\n"
            f"Trạng thái: {status}\n"
            f"Thời gian tìm kiếm: {self.search_time:.4f} giây\n"
            f"Bộ nhớ tiêu thụ đỉnh: {self.peak_memory_kb:.2f} KB\n"
            f"Số nút đã mở rộng: {self.expanded_nodes}\n"
            f"Số nút đã sinh: {self.generated_nodes}\n"
            f"Độ dài lời giải (Số bước): {self.solution_length}\n"
            f"Tổng chi phí đường đi: {self.solution_cost:.2f}\n"
        )
