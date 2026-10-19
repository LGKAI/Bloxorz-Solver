# Bloxorz Solver

Đồ án Cơ sở AI

🎥 **Video Demo:** [Xem trên YouTube](https://youtu.be/bloxorzsolver)

---

## 1. Giới thiệu tổng quan
Dự án giải bài toán game **Bloxorz** bằng các giải thuật tìm kiếm trong không gian trạng thái:
- **Cơ chế game đầy đủ:** Ô thường, ô cam dễ vỡ (Fragile), hố đích (Goal), hệ thống cầu nối (Bridges), 3 loại công tắc (Tròn mềm, X nặng, Phân thân) và cơ chế tách - ghép 2 khối lập phương $1 \times 1 \times 1$.
- **4 Thuật toán tìm kiếm:**
  - **BFS:** Tìm đường ngắn nhất theo số bước (tối ưu số bước).
  - **DFS / IDS:** Tìm kiếm theo chiều sâu kết hợp tập đã duyệt (Visited Set) chống lặp chu trình.
  - **UCS:** Tìm đường đi tối ưu theo hàm chi phí phi đồng nhất.
  - **A\*:** Tìm kiếm theo kinh nghiệm với hàm heuristic $h(n)$ chấp nhận được (Admissible) và nhất quán (Consistent).
- **Giao diện 3D Isometric (Pygame):** Đồ họa 3D khối hộp có độ dày, bóng đổ, tự động mô phỏng khối lăn về đích khi bấm giải (theo đúng FAQ môn học), hỗ trợ chơi thủ công và tua bước.

---

## 2. Cấu trúc thư mục mã nguồn

```text
Source/
├── levels/                     # 33 màn chơi chuẩn của Bloxorz (map01.txt -> map33.txt)
├── src/
│   ├── core/                   # Logic mô phỏng game
│   │   ├── block.py            # Trạng thái khối (Đứng, Ngang, Dọc, Phân thân) & phép lăn
│   │   ├── game_state.py       # Quản lý trạng thái, cầu, công tắc, hàm chi phí
│   │   └── map_loader.py       # Đọc bản đồ và cấu hình công tắc - cầu nối (ManaBoa)
│   ├── solvers/                # Triển khai các thuật toán
│   │   ├── base_solver.py      # Cấu trúc lưu trữ kết quả & chỉ số đo lường
│   │   ├── bfs.py              # BFS (Goal test on generation)
│   │   ├── dfs.py              # DFS & IDS
│   │   ├── ucs.py              # Uniform-Cost Search
│   │   └── astar.py            # A* với Heuristic khoảng cách lưới nới lỏng
│   └── gui/                    # Giao diện đồ họa Pygame
│       ├── renderer.py         # Dựng hình 3D Isometric, đa giác 3 chiều, đổ bóng
│       └── app.py              # Xử lý sự kiện, đa luồng solver, tự động chạy lời giải
├── experiments/                # Kết quả đánh giá hiệu năng
│   ├── results.csv             # Bảng dữ liệu thô (CSV)
│   ├── experiment_report.md    # Bảng số liệu tổng hợp Markdown
│   └── plots/                  # 4 biểu đồ PNG (Thời gian, Bộ nhớ, Nút mở rộng, Số bước)
├── tests/                      # Bộ kiểm thử tự động
│   ├── test_core.py            # Unit test 12 phép lăn và luật va chạm cơ bản
│   └── verify_all_levels.py    # Kiểm chứng độ tối ưu và tính hợp lệ trên cả 33 màn
├── main.py                     # File chạy chính (Mặc định mở GUI, hỗ trợ CLI)
├── experiment.py               # Script chạy thực nghiệm tự động trên 4 nhóm màn chơi
├── requirements.txt            # Thư viện phụ thuộc (pygame, matplotlib, numpy)
└── README.md                   # Hướng dẫn sử dụng dự án
```

---

## 3. Cài đặt & Khởi chạy

### 3.1. Cài đặt môi trường
- Python 3.8+ (khuyên dùng Python 3.10 – 3.12).
- Cài đặt thư viện:
```bash
pip install -r requirements.txt
```

### 3.2. Chạy giao diện đồ họa (GUI)
```bash
python main.py
```
- **Thao tác trên GUI:**
  - Nhấp chọn thuật toán: **Solve BFS**, **Solve DFS**, **Solve UCS**, **Solve A\***.
  - Khi tìm thấy lời giải, **khối sắt sẽ tự động lăn từng bước về đích** (theo đúng giải đáp FAQ của Thầy).
  - Sử dụng các nút điều khiển lời giải: `> Play` / `|| Pause`, `< Back`, `Step >`, tốc độ `1x`, `2x`.
  - Nút **New Game** để chuyển màn, **Restart** để đặt lại màn.
  - **Phóng to toàn màn hình:** Bấm nút **Fullscreen** trên góc phải (hoặc phím **F11** / nút Maximize của cửa sổ), bấm **Esc** hoặc **F11** để thu nhỏ.
  - **Phím chơi thủ công:** Phím mũi tên hoặc `W/A/S/D` để lăn, phím `Space` để đổi khối khi phân thân, phím `R` để chơi lại, phím `U` để đi lùi (undo).

### 3.3. Chạy qua dòng lệnh (CLI)
Cú pháp:
```bash
python main.py <màn_chơi> <thuật_toán>
```
Ví dụ:
```bash
python main.py 01 BFS
python main.py 02 UCS
python main.py 04 DFS
python main.py 08 A*
```

### 3.4. Chạy kiểm thử & Thực nghiệm
- Chạy toàn bộ Unit Test:
  ```bash
  python -m unittest discover tests
  ```
- Chạy kiểm chứng trên toàn bộ 33 màn:
  ```bash
  python tests/verify_all_levels.py
  ```
- Chạy đo đạc thực nghiệm và vẽ biểu đồ:
  ```bash
  python experiment.py
  ```

---

## 4. Mô hình hóa bài toán (Search Formalization)

- **Trạng thái ($s$):** Cặp `(BlockState, BridgeState)`
  - `BlockState`:
    - Khối nguyên: `(Orientation, r, c)` với `Orientation` $\in$ {`STANDING`, `HORIZONTAL`, `VERTICAL`}.
    - Khối phân thân: `(SPLIT, sorted((r0, c0), (r1, c1)))`.
  - `BridgeState`: `tuple` boolean thể hiện trạng thái Đóng/Mở của từng cây cầu.
- **Không gian hành động ($A$):** 4 hướng {`UP`, `DOWN`, `LEFT`, `RIGHT`}. Khi phân thân, hành động có dạng `(cube_index, direction)`.
- **Luật chuyển trạng thái:**
  - Khối đứng lăn sẽ thành khối nằm (chiếm 2 ô). Khối nằm lăn dọc theo trục dài sẽ thành khối đứng (chiếm 1 ô), lăn theo trục ngắn sẽ giữ nguyên hướng nằm.
  - Khối đứng trên ô cam (Fragile - số 2) sẽ làm sập sàn $\to$ hành động không hợp lệ. Khối nằm hoặc khối $1 \times 1 \times 1$ đi qua an toàn.
  - Khi 2 khối phân thân đứng ở hai ô kề nhau, chúng tự động hợp nhất thành khối $1 \times 1 \times 2$.
- **Kiểm tra đích (Goal Test):** Khối ở trạng thái `STANDING` tại tọa độ ô đích `(goal_r, goal_c)`.

---

## 5. Thiết kế thuật toán tìm kiếm

### 5.1. BFS (Breadth-First Search)
- Sử dụng hàng đợi `collections.deque` FIFO.
- Kiểm tra đích ngay khi sinh nút (Goal Test on Generation) để giảm 1 tầng duyệt, đảm bảo tối ưu số bước đi.

### 5.2. DFS & IDS
- Sử dụng ngăn xếp LIFO và tập `visited` lưu trạng thái đã duyệt trên nhánh để tránh lặp vô tận.
- Hỗ trợ giải thuật IDS (Iterative Deepening Search) tăng dần giới hạn độ sâu.

### 5.3. UCS (Uniform-Cost Search)
- Sử dụng hàng đợi ưu tiên `heapq` theo chi phí tích lũy $g(n)$.
- **Hàm chi phí phi đồng nhất (Non-uniform cost):**
  $$c(s \to s') = 1.0 + \text{Penalty}_{\text{fragile}} + \text{Penalty}_{\text{standing}}$$
  - Chi phí cơ bản: $1.0$ cho mỗi bước.
  - Phạt ô cam ($\text{Penalty}_{\text{fragile}} = +1.0$): Phạt khi lăn qua ô cam nhằm hạn chế rủi ro sập sàn và tránh giới hạn đường đi tiếp theo.
  - Phạt dựng đứng ($\text{Penalty}_{\text{standing}} = +0.2$): Phạt hành vi dựng đứng do nâng trọng tâm và quán tính lớn hơn lăn nằm.

### 5.4. A\* Search & Hàm Heuristic
- **Hàm Heuristic:** $h(s) = \text{Relaxed Grid BFS Distance} + \text{Orientation Penalty}$
  - *Relaxed Grid Distance:* Tính khoảng cách ngắn nhất từ mọi ô trên lưới về đích thông qua 1 lần BFS ngược từ ô đích (coi các công tắc phân thân như cạnh dịch chuyển 0-chi phí). Vì mỗi bước khối dịch chuyển tối đa 2 ô:
    $$h_1(s) = \left\lceil \frac{D_{\text{grid}}}{2} \right\rceil$$
  - *Orientation Penalty:* Khối nằm đè lên đích chưa thể thắng ngay mà phải lật ra rồi lật lại để đứng ($\to h(s) \ge 2.0$).
- **Tính chất:** $h(s)$ được đảm bảo **chấp nhận được (Admissible)** và **nhất quán (Consistent)**, tức $h(s) \le c(s, a, s') + h(s')$. Lời giải của A\* luôn bảo đảm tối ưu tuyệt đối.

---

## 6. Tóm tắt kết quả thực nghiệm

Chạy thử nghiệm trên 13 màn chơi đại diện cho 4 nhóm độ khó:

| Nhóm | Màn | BFS (Bước / Thời gian) | DFS (Bước / Thời gian) | UCS (Chi phí / Nút mở) | A* (Chi phí / Nút mở) |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Nhóm 1: Cơ bản** | `map01` | **7** bước (0.003s) | 34 bước (0.002s) | 7.4 (74 nút) | **7.4 (43 nút)** |
| | `map03` | **16** bước (0.003s) | 39 bước (0.004s) | 17.2 (102 nút) | **17.2 (93 nút)** |
| | `map06` | **35** bước (0.003s) | 54 bước (0.002s) | 37.2 (110 nút) | **37.2 (105 nút)** |
| **Nhóm 2: Ô cam** | `map04` | **28** bước (0.002s) | 28 bước (0.003s) | 43.0 (70 nút) | **43.0 (69 nút)** |
| | `map13` | 46 bước (0.004s) | 66 bước (0.003s) | **59.4 (139 nút)** | **59.4 (134 nút)** |
| **Nhóm 3: Công tắc** | `map02` | **17** bước (0.012s) | 64 bước (0.014s) | 18.4 (274 nút) | **18.4 (199 nút)** |
| | `map05` | **33** bước (0.010s) | 175 bước (0.009s) | 35.4 (310 nút) | **35.4 (248 nút)** |
| | `map07` | **44** bước (0.006s) | 61 bước (0.006s) | 47.2 (179 nút) | **47.2 (177 nút)** |
| | `map11` | **47** bước (0.006s) | 51 bước (0.005s) | 50.4 (187 nút) | **50.4 (187 nút)** |
| **Nhóm 4: Phân thân** | `map08` | **10** bước (0.047s) | 50 bước (0.005s) | 10.4 (595 nút) | **10.4 (97 nút)** |
| | `map09` | **24** bước (0.071s) | 100 bước (0.030s) | 24.8 (750 nút) | **24.8 (532 nút)** |
| | `map10` | **57** bước (0.382s) | 279 bước (0.049s) | 58.4 (3467 nút) | **58.4 (2323 nút)** |
| | `map15` | **57** bước (0.272s) | 436 bước (0.068s) | 59.0 (2680 nút) | **59.0 (1549 nút)** |

> **Nhận xét chính:**
> 1. **BFS** luôn tìm ra số bước đi ngắn nhất.
> 2. **UCS** và **A\*** luôn tìm ra cùng một giải pháp có tổng chi phí nhỏ nhất. Trên các màn có ô cam (như `map13`), UCS và A\* chủ động đi đường vòng để né ô cam (chi phí 59.4 < chi phí 60.0 của BFS).
> 3. **A\*** mở rộng ít nút hơn đáng kể so với UCS và BFS (ví dụ tại `map08`: A\* chỉ mở 97 nút so với 595 nút của UCS, giảm hơn 83% không gian duyệt).