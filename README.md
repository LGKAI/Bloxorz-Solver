# Bloxorz Solver

Đồ án Cơ sở AI

🎥 **Video Demo:** [Xem trên YouTube](https://youtu.be/ORCcDhS5t_M?si=MCSsTSRV6_NXOrRQ)  

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
│   │   └── astar.py            # A* với Heuristic khoảng cách lưới nới lỏng (Relaxed Grid BFS)
│   └── gui/                    # Giao diện đồ họa Pygame & Animation 3D
│       ├── icon.png            # Biểu tượng khối hộp 3D Isometric chuẩn nét cao
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

> 📖 **Ghi chú:** Chi tiết về mô hình hóa không gian trạng thái, phân tích thuật toán và kết quả thực nghiệm được trình bày đầy đủ trong file Report của đồ án.
> 
> 🎮 **Chúc bạn có những trải nghiệm giải đố Bloxorz vui vẻ!**