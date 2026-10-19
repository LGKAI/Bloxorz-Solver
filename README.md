# Bloxorz Solver

Đồ án Cơ sở AI

🎥 **Video Demo:** [Xem trên YouTube](https://youtu.be/bloxorzsolver)  

---

## 1. Giới thiệu tổng quan
Dự án giải bài toán game **Bloxorz** bằng các giải thuật tìm kiếm trong không gian trạng thái:
- **Cơ chế game đầy đủ:** Ô thường, ô cam dễ vỡ (Fragile), hố đích (Goal), hệ thống cầu nối (Bridges), 3 loại công tắc (Tròn mềm, X nặng, Phân thân) và cơ chế tách - ghép 2 khối lập phương $1 \times 1 \times 1$.
- **4 Thuật toán tìm kiếm độc lập:**
  - **BFS:** Tìm đường ngắn nhất theo số bước (tối ưu số bước đi tuyệt đối với kỹ thuật Goal Test on Generation).
  - **DFS / IDS:** Tìm kiếm theo chiều sâu kết hợp tập đã duyệt (Visited Set) chống lặp chu trình, hỗ trợ tìm kiếm sâu dần (Iterative Deepening Search).
  - **UCS:** Tìm đường đi tối ưu theo hàm chi phí phi đồng nhất (ưu tiên né ô cam dễ vỡ, hạn chế dựng đứng).
  - **A\*:** Tìm kiếm có thông tin với hàm Heuristic $h(n)$ khoảng cách lưới nới lỏng (Relaxed Grid BFS Distance) đảm bảo tính chấp nhận được (Admissible) và nhất quán đơn điệu (Consistent).
- **Giao diện 3D Isometric chuẩn phong cách Bloxorz kinh điển (Pygame):**
  - **Góc nhìn 3D & Nền đỏ huyền thoại:** Hệ trục cơ sở $(U, V, H, D)$ theo góc nhìn chuẩn của game Bloxorz gốc, nền dải gradient đỏ rực rỡ, tự động co giãn và căn giữa thích ứng (Adaptive scaling) cho toàn bộ 33 màn chơi.
  - **Hệ thống hoạt ảnh 3D chuyển động chân thực (Animation Engine):**
    - *Rolling Animation:* Lăn lật 3D 90° quanh trục mép sàn mượt mà theo từng khung hình (cả khi chơi thủ công và Replay tự động).
    - *Victory Sink:* Khối đứng thẳng thụt chìm dần vào lòng hố đích khi chiến thắng.
    - *Edge Fall:* Khối lật quá mép rơi nhào lộn theo gia tốc trọng trường xuống vực thẳm.
    - *Fragile Collapse:* Ô cam sụp nứt kèm hiệu ứng chùm hạt mảnh vỡ (`Particle`) văng tung tóe và khối rơi tự do.
    - *Board Restart Animation:* Chuỗi 5 giai đoạn sụp đổ và tái lập sàn (Fall $\to$ Wait $\to$ Rise $\to$ Flash $\to$ Spawn) khi thua hoặc khởi động lại (bấm phím bất kỳ hoặc click để bỏ qua ngay).
    - *Stage Transition Modal:* Hộp thoại chúc mừng chuyển màn tự động đếm giờ hoặc bấm phím để tiếp tục.
  - **Bộ dựng font chữ an toàn (SafeFont):** Sử dụng Pillow và bộ nhớ đệm LRU Cache đạt 60 FPS mượt mà, hỗ trợ tiếng Việt Unicode sắc nét, chống lỗi Circular Import / Segmentation Fault trên Python 3.14.
  - **Hỗ trợ toàn màn hình (Fullscreen):** Nút phóng to / thu nhỏ hoặc phím **F11** / nút Maximize của cửa sổ.

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
│   ├── solvers/                # Triển khai các thuật toán tìm kiếm
│   │   ├── base_solver.py      # Cấu trúc lưu trữ kết quả & chỉ số đo lường
│   │   ├── bfs.py              # BFS (Goal test on generation)
│   │   ├── dfs.py              # DFS & IDS (Depth-Limited & Iterative Deepening)
│   │   ├── ucs.py              # Uniform-Cost Search (Ưu tiên chi phí tích lũy g(n))
│   │   ├── astar.py            # A* với Heuristic khoảng cách lưới nới lỏng
│   │   └── heuristics.py       # Tính toán hàm Heuristic Admissible & Consistent
│   └── gui/                    # Giao diện đồ họa Pygame & Animation 3D
│       ├── renderer.py         # Dựng hình 3D Isometric chuẩn Bloxorz, nền gradient đỏ, adaptive scaling
│       ├── animator.py         # Hoạt ảnh lăn khối 90°, thụt hố đích, rơi vực và sập sàn cam nứt vỡ
│       ├── board_animator.py   # Chuỗi hoạt ảnh tái lập màn chơi (Board Disintegration & Rebuild)
│       ├── safe_font.py        # Bộ dựng font chữ an toàn bằng Pillow, cache tốc độ cao 60 FPS
│       └── app.py              # Giao diện chính, đa luồng solver, điều khiển replay, chuyển màn
├── experiments/                # Kết quả đánh giá hiệu năng
│   ├── results.csv             # Bảng dữ liệu thô (CSV)
│   ├── experiment_report.md    # Bảng số liệu tổng hợp Markdown
│   └── plots/                  # 4 biểu đồ PNG (Thời gian, Bộ nhớ, Nút mở rộng, Số bước)
├── tests/                      # Bộ kiểm thử tự động (20 test cases, pass 100%)
│   ├── test_core.py            # 10 Unit test kiểm tra logic lăn khối, va chạm, phân thân, công tắc
│   ├── test_animator.py        # 7 Unit test kiểm tra góc quay 3D và lifecycle animation của khối
│   ├── test_board_animator.py  # 3 Unit test kiểm tra chuỗi 5 giai đoạn tái lập bàn cờ
│   └── verify_all_levels.py    # Kiểm chứng độ tối ưu và tính hợp lệ trên cả 33 màn
├── main.py                     # File chạy chính (Mặc định mở GUI, hỗ trợ CLI)
├── experiment.py               # Script chạy thực nghiệm tự động trên 4 nhóm màn chơi
├── requirements.txt            # Thư viện phụ thuộc (pygame, matplotlib, numpy, Pillow)
└── README.md                   # Hướng dẫn sử dụng dự án
```

---

## 3. Cài đặt & Khởi chạy

### 3.1. Cài đặt môi trường
- Yêu cầu Python $\ge 3.8$ (khuyên dùng Python 3.10 – 3.12).
- Cài đặt các thư viện phụ thuộc:
```bash
pip install -r requirements.txt
```

### 3.2. Chạy giao diện đồ họa (GUI)
```bash
python main.py
```
- **Thao tác trên GUI:**
  - Nhấp chọn thuật toán: **Solve BFS**, **Solve DFS**, **Solve UCS**, **Solve A\***.
  - Quá trình tìm kiếm chạy ngầm trên **Background Thread**, giữ giao diện đạt 60 FPS mượt mà không bị treo.
  - Khi tìm thấy lời giải, **khối sắt sẽ tự động lăn từng bước về đích** kèm hiệu ứng lăn 3D mượt mà.
  - Sử dụng các nút điều khiển lời giải: `> Play` / `|| Pause`, `< Back`, `Step >`, tốc độ `1x`, `2x`.
  - Nút **New Game** để chuyển màn, **Restart** để đặt lại màn chơi.
  - **Phóng to toàn màn hình:** Bấm nút **Fullscreen** trên góc phải (hoặc phím **F11** / nút Maximize của cửa sổ), bấm **Esc** hoặc **F11** để thu nhỏ.
  - **Phím chơi thủ công:** Phím mũi tên hoặc `W/A/S/D` để lăn khối, phím `Space` để đổi khối khi phân thân, phím `R` để chơi lại, phím `U` để đi lùi (undo).
  - Khi khối rơi khỏi sàn, bàn cờ tự động chạy hoạt ảnh sụp đổ và lắp ráp lại (bấm phím bất kỳ hoặc click chuột để tiếp tục ngay).

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
- Chạy toàn bộ 20 bài Unit Test tự động:
  ```bash
  python -m unittest discover tests
  ```
- Chạy kiểm chứng trên toàn bộ 33 màn chơi của game gốc:
  ```bash
  python tests/verify_all_levels.py
  ```
- Chạy đo đạc thực nghiệm và vẽ 4 biểu đồ so sánh:
  ```bash
  python experiment.py
  ```

---

## 4. Mô hình hóa bài toán (Search Formalization)

- **Trạng thái ($s$):** Cặp `(BlockState, BridgeState)`
  - `BlockState`:
    - Khối nguyên: `(Orientation, r, c)` với `Orientation` $\in$ {`STANDING`, `HORIZONTAL`, `VERTICAL`}.
    - Khối phân thân: `(SPLIT, sorted((r0, c0), (r1, c1)))` theo thứ tự từ điển triệt tiêu nhánh đối xứng.
  - `BridgeState`: `tuple` boolean bất biến thể hiện trạng thái Đóng/Mở của từng cây cầu, giúp băm trạng thái và tra cứu $O(1)$ mà không cần copy ma trận bản đồ.
- **Không gian hành động ($A$):** 4 hướng {`UP`, `DOWN`, `LEFT`, `RIGHT`}. Khi phân thân, hành động có dạng `(cube_index, direction)`.
- **Luật chuyển trạng thái:**
  - Khối đứng lăn sẽ thành khối nằm (chiếm 2 ô). Khối nằm lăn dọc theo trục dài sẽ thành khối đứng (chiếm 1 ô), lăn theo trục ngắn sẽ giữ nguyên hướng nằm.
  - Khối đứng trên ô cam (Fragile - số 2) sẽ làm sập sàn $\to$ hành động không hợp lệ. Khối nằm hoặc khối nhỏ $1 \times 1 \times 1$ đi qua an toàn.
  - Khi 2 khối phân thân đứng ở hai ô kề nhau, chúng tự động hợp nhất thành khối $1 \times 1 \times 2$.
- **Kiểm tra đích (Goal Test):** Khối ở trạng thái `STANDING` tại tọa độ ô đích `(goal_r, goal_c)`.

---

## 5. Thiết kế thuật toán tìm kiếm

### 5.1. BFS (Breadth-First Search)
- Sử dụng hàng đợi `collections.deque` FIFO.
- Kiểm tra đích ngay khi sinh nút (Goal Test on Generation) để giảm 1 tầng duyệt, đảm bảo tối ưu số bước đi tuyệt đối.

### 5.2. DFS & IDS
- Sử dụng ngăn xếp LIFO và tập `visited` lưu trạng thái đã duyệt trên nhánh để tránh lặp vô tận.
- Hỗ trợ giải thuật IDS (Iterative Deepening Search) tăng dần giới hạn độ sâu, kết hợp ưu điểm tiết kiệm bộ nhớ của DFS với tính tối ưu số bước của BFS.

### 5.3. UCS (Uniform-Cost Search)
- Sử dụng hàng đợi ưu tiên `heapq` theo chi phí tích lũy $g(n)$.
- Kiểm tra đích khi mở rộng nút (Goal Test on Expansion) bảo đảm tính tối ưu về chi phí.
- **Hàm chi phí phi đồng nhất (Non-uniform cost):**
  $$c(s \to s') = 1.0 + \text{Penalty}_{\text{fragile}} + \text{Penalty}_{\text{standing}}$$
  - Chi phí cơ bản: $1.0$ cho mỗi bước.
  - Phạt ô cam ($\text{Penalty}_{\text{fragile}} = +1.0$): Phạt khi lăn qua ô cam nhằm ưu tiên đường đi an toàn, giảm thiểu rủi ro sập sàn.
  - Phạt dựng đứng ($\text{Penalty}_{\text{standing}} = +0.2$): Phạt hành vi dựng đứng do nâng trọng tâm và tiêu hao quán tính lớn hơn lăn nằm.

### 5.4. A\* Search & Hàm Heuristic
- **Hàm Heuristic:** $h(s) = \text{Relaxed Grid BFS Distance} + \text{Orientation Penalty}$
  - *Relaxed Grid Distance:* Tính khoảng cách ngắn nhất từ mọi ô trên lưới về đích thông qua 1 lần BFS ngược từ ô đích (coi các công tắc phân thân như cạnh dịch chuyển 0-chi phí). Vì mỗi bước khối dịch chuyển tối đa 2 ô:
    $$h_1(s) = \left\lceil \frac{D_{\text{grid}}}{2} \right\rceil$$
  - *Orientation Penalty:* Khối nằm đè lên đích chưa thể thắng ngay mà phải lật ra rồi lật lại để đứng ($\to h(s) \ge 2.0$).
- **Tính chất:** $h(s)$ được chứng minh **chấp nhận được (Admissible)** và **nhất quán đơn điệu (Monotonic Consistent)**, tức $h(s) \le c(s, a, s') + h(s')$. Lời giải của A\* luôn bảo đảm tối ưu tuyệt đối mà không cần mở lại các nút trong tập đóng.

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
> 1. **BFS** luôn tìm ra số bước đi ngắn nhất tuyệt đối.
> 2. **UCS** và **A\*** luôn tìm ra cùng một giải pháp có tổng chi phí nhỏ nhất. Trên các màn có ô cam (như `map13`), UCS và A\* chủ động đi đường vòng để né ô cam (chi phí 59.4 < chi phí 60.0 của BFS).
> 3. **A\*** mở rộng ít nút hơn đáng kể so với UCS và BFS (ví dụ tại `map08`: A\* chỉ mở 97 nút so với 595 nút của UCS, giảm hơn 83.7% không gian duyệt).