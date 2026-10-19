"""
Module: block.py
Mô tả: Định nghĩa cấu trúc khối hộp Bloxorz (1x1x2), các hướng quay,
      luật chuyển hướng khi lăn và trạng thái phân thân (Split) thành 2 khối 1x1x1.
"""

from enum import Enum
from typing import List, Tuple, Optional


class Orientation(Enum):
    """
    Các trạng thái hướng quay của khối Bloxorz:
    - STANDING: Khối đứng thẳng trên 1 ô (r, c), chiều cao 2 đơn vị.
    - HORIZONTAL: Khối nằm ngang chiếm 2 ô liền kề cùng một hàng: (r, c) và (r, c + 1).
    - VERTICAL: Khối nằm dọc chiếm 2 ô liền kề cùng một cột: (r, c) và (r + 1, c).
    - SPLIT: Khối bị phân tách thành hai khối lập phương 1x1x1 riêng biệt.
    """
    STANDING = "STANDING"
    HORIZONTAL = "HORIZONTAL"
    VERTICAL = "VERTICAL"
    SPLIT = "SPLIT"


class Direction(Enum):
    """Bốn hướng di chuyển cơ bản."""
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class BlockState:
    """
    Đại diện cho trạng thái vị trí và hướng của khối Bloxorz.
    - Với khối đơn: (r, c) là tọa độ góc trên-trái (ô có chỉ số hàng và cột nhỏ nhất).
    - Với khối phân thân: (r0, c0) là vị trí khối lập phương 1, (r1, c1) là vị trí khối 2.
    """

    def __init__(
        self,
        orientation: Orientation,
        r: int,
        c: int,
        r1: Optional[int] = None,
        c1: Optional[int] = None,
        active_cube: int = 0
    ):
        self.orientation = orientation
        self.r = r
        self.c = c
        self.r1 = r1
        self.c1 = c1
        self.active_cube = active_cube  # 0 hoặc 1 (dành cho chế độ chơi thủ công phân thân)

    def occupied_cells(self) -> List[Tuple[int, int]]:
        """
        Trả về danh sách các ô (row, col) mà khối đang chiếm giữ trên sàn đấu.
        """
        if self.orientation == Orientation.STANDING:
            return [(self.r, self.c)]
        elif self.orientation == Orientation.HORIZONTAL:
            return [(self.r, self.c), (self.r, self.c + 1)]
        elif self.orientation == Orientation.VERTICAL:
            return [(self.r, self.c), (self.r + 1, self.c)]
        elif self.orientation == Orientation.SPLIT:
            return [(self.r, self.c), (self.r1, self.c1)]
        return []

    def canonical_key(self) -> tuple:
        """
        Trả về tuple đặc trưng duy nhất của khối để làm khóa băm (hash key) trong visited set.
        Với trạng thái SPLIT, sắp xếp tọa độ 2 khối để tránh trùng lặp trạng thái đối xứng.
        """
        if self.orientation != Orientation.SPLIT:
            return (self.orientation.value, self.r, self.c)
        else:
            cube1 = (self.r, self.c)
            cube2 = (self.r1, self.c1)
            cubes = tuple(sorted([cube1, cube2]))
            return (Orientation.SPLIT.value, cubes)

    def roll(self, direction: Direction) -> "BlockState":
        """
        Thực hiện lăn khối (đối với khối nguyên vẹn 1x1x2) theo một trong 4 hướng:
        - STANDING khi lăn sẽ đổ xuống thành HORIZONTAL hoặc VERTICAL (chiếm 2 ô).
        - HORIZONTAL khi lăn theo phương ngang sẽ đứng lên; lăn theo phương dọc thì trượt ngang.
        - VERTICAL khi lăn theo phương dọc sẽ đứng lên; lăn theo phương ngang thì trượt dọc.
        """
        if self.orientation == Orientation.SPLIT:
            raise ValueError("Khối đang ở trạng thái phân thân, hãy dùng move_cube().")

        r, c = self.r, self.c
        ori = self.orientation

        if ori == Orientation.STANDING:
            if direction == Direction.UP:
                # Đổ về phía trên -> chiếm (r - 2, c) và (r - 1, c)
                return BlockState(Orientation.VERTICAL, r - 2, c)
            elif direction == Direction.DOWN:
                # Đổ về phía dưới -> chiếm (r + 1, c) và (r + 2, c)
                return BlockState(Orientation.VERTICAL, r + 1, c)
            elif direction == Direction.LEFT:
                # Đổ sang trái -> chiếm (r, c - 2) và (r, c - 1)
                return BlockState(Orientation.HORIZONTAL, r, c - 2)
            elif direction == Direction.RIGHT:
                # Đổ sang phải -> chiếm (r, c + 1) và (r, c + 2)
                return BlockState(Orientation.HORIZONTAL, r, c + 1)

        elif ori == Orientation.HORIZONTAL:
            if direction == Direction.UP:
                # Lăn cạnh dài lên trên -> vẫn nằm ngang ở hàng trên
                return BlockState(Orientation.HORIZONTAL, r - 1, c)
            elif direction == Direction.DOWN:
                # Lăn cạnh dài xuống dưới -> vẫn nằm ngang ở hàng dưới
                return BlockState(Orientation.HORIZONTAL, r + 1, c)
            elif direction == Direction.LEFT:
                # Dựng đứng sang trái -> đứng tại (r, c - 1)
                return BlockState(Orientation.STANDING, r, c - 1)
            elif direction == Direction.RIGHT:
                # Dựng đứng sang phải -> đứng tại (r, c + 2)
                return BlockState(Orientation.STANDING, r, c + 2)

        elif ori == Orientation.VERTICAL:
            if direction == Direction.UP:
                # Dựng đứng lên trên -> đứng tại (r - 1, c)
                return BlockState(Orientation.STANDING, r - 1, c)
            elif direction == Direction.DOWN:
                # Dựng đứng xuống dưới -> đứng tại (r + 2, c)
                return BlockState(Orientation.STANDING, r + 2, c)
            elif direction == Direction.LEFT:
                # Lăn cạnh dài sang trái -> vẫn nằm dọc ở cột bên trái
                return BlockState(Orientation.VERTICAL, r, c - 1)
            elif direction == Direction.RIGHT:
                # Lăn cạnh dài sang phải -> vẫn nằm dọc ở cột bên phải
                return BlockState(Orientation.VERTICAL, r, c + 1)

        raise ValueError(f"Không xác định hướng di chuyển: {direction}")

    def move_cube(self, cube_index: int, direction: Direction) -> "BlockState":
        """
        Di chuyển 1 trong 2 khối lập phương khi đang phân thân (SPLIT):
        - cube_index = 0: di chuyển khối tại (r, c)
        - cube_index = 1: di chuyển khối tại (r1, c1)
        Sau khi di chuyển, kiểm tra xem hai khối có kề cạnh nhau để sáp nhập (merge) hay không.
        """
        if self.orientation != Orientation.SPLIT:
            raise ValueError("Chỉ di chuyển từng khối khi đang ở trạng thái SPLIT.")

        r0, c0 = self.r, self.c
        r1, c1 = self.r1, self.c1

        dr, dc = 0, 0
        if direction == Direction.UP:
            dr = -1
        elif direction == Direction.DOWN:
            dr = 1
        elif direction == Direction.LEFT:
            dc = -1
        elif direction == Direction.RIGHT:
            dc = 1

        if cube_index == 0:
            new_r0, new_c0 = r0 + dr, c0 + dc
            new_r1, new_c1 = r1, c1
        else:
            new_r0, new_c0 = r0, c0
            new_r1, new_c1 = r1 + dr, c1 + dc

        new_block = BlockState(
            Orientation.SPLIT,
            new_r0,
            new_c0,
            new_r1,
            new_c1,
            active_cube=cube_index
        )
        return new_block.check_merge()

    def check_merge(self) -> "BlockState":
        """
        Kiểm tra hai khối phân thân có kề cạnh nhau (trên-dưới hoặc trái-phải) hay không.
        Nếu có, sáp nhập trở lại thành khối 1x1x2 (HORIZONTAL hoặc VERTICAL).
        """
        if self.orientation != Orientation.SPLIT:
            return self

        r0, c0 = self.r, self.c
        r1, c1 = self.r1, self.c1

        # Kề nhau theo phương ngang (cùng hàng, cột chênh nhau 1)
        if r0 == r1 and abs(c0 - c1) == 1:
            left_c = min(c0, c1)
            return BlockState(Orientation.HORIZONTAL, r0, left_c)

        # Kề nhau theo phương dọc (cùng cột, hàng chênh nhau 1)
        if c0 == c1 and abs(r0 - r1) == 1:
            top_r = min(r0, r1)
            return BlockState(Orientation.VERTICAL, top_r, c0)

        return self

    def __repr__(self) -> str:
        if self.orientation != Orientation.SPLIT:
            return f"Block({self.orientation.value}, pos=({self.r}, {self.c}))"
        return f"Block(SPLIT, c0=({self.r}, {self.c}), c1=({self.r1}, {self.c1}))"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, BlockState):
            return False
        return self.canonical_key() == other.canonical_key()

    def __hash__(self) -> int:
        return hash(self.canonical_key())
