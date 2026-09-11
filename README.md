# SOICT 2026 - Integrated Passenger and Parcel Transportation (PDVRPTW)

Dự án giải bài toán **"Vận tải Tích hợp Hành khách và Bưu kiện"** thuộc Cuộc thi Sinh viên SOICT 2026. Mục tiêu chính là xây dựng lịch trình tối ưu cho đội xe taxi nhằm tối đa hóa tổng lợi nhuận (Benefit) dựa trên các ràng buộc khắt khe về thời gian, sức chứa và quy tắc chở khách trực tiếp.

---

## 👥 Thành viên Thực hiện
* **Bùi Thế Dũng**
* **Nguyễn Hà Thu**

---

## 📌 Tóm Tắt Bài Toán

* **Mô hình toán học:** Selective Pickup and Delivery Vehicle Routing Problem with Time Windows (PDVRPTW).
* **Quyết định chính:**
  1. Chọn tập hợp hành khách ($S_N$) và bưu kiện ($S_M$) thu về lợi nhuận cao nhất.
  2. Phân công từng yêu cầu cho từng taxi $k$.
  3. Lập thứ tự các điểm dừng $R_k$ thỏa mãn tất cả các ràng buộc cứng.
* **Ràng buộc quan trọng:**
  * **Hành khách:** Taxi phải đi **trực tiếp** từ $P_i^n$ đến $D_i^n$, không được rẽ ngang hay trả/nhận bưu kiện giữa chừng.
  * **Bưu kiện:** $P_j^h$ phải nằm trước $D_j^h$, tổng tải trọng $load_k \le Q_k$ tại mọi thời điểm.
  * **Khung thời gian:** Tuân thủ tuyệt đối thời gian mở/đóng cửa dịch vụ.

---

## 💡 Định Hướng Thuật Toán

1. **Chính (Primary): Adaptive Large Neighborhood Search (ALNS)**
   * **Destroy Operators:** Random Destroy, Worst Cost Destroy, Shaw Destroy.
   * **Repair Operators:** Greedy Repair, Regret-2 / Regret-3 Insertion.
   * Cập nhật trọng số toán tử động theo điểm thưởng mỗi vòng lặp.

2. **Dự phòng (Backup): Greedy Insertion + Simulated Annealing (SA)**
   * Khởi tạo bằng **Greedy/Random Insertion** đảm bảo tính hợp lệ.
   * Cải thiện nghiệm bằng **Local Search** (Relocate, Swap, 2-opt) kết hợp **Simulated Annealing** để thoát bẫy tối ưu cục bộ.
   * Tích hợp cơ chế **Timeout Guard** để tránh lỗi vượt quá thời gian cho phép (TLE).

---

## 📅 Lộ Trình Phát Triển (Timeline)

* **15/09/2026:** Hạn chót đăng ký tham gia.
* **20/09/2026 – 20/10/2026 (Giai đoạn Probation):**
  * **Tuần 1:** Xây dựng Data Structure, Checker & Baseline Greedy.
  * **Tuần 2:** Tối ưu hóa cục bộ với Local Search (Swap/Relocate).
  * **Tuần 3:** Tích hợp bộ giải ALNS cốt lõi.
  * **Tuần 4:** Fine-tune tham số & Tối ưu hiệu năng bằng PyPy/NumPy.
* **01/11/2026 – 04/11/2026 (Main Competition):** Chạy thử nghiệm trên các Edge Cases và chốt bản nộp chính thức.

---

## 📁 Cấu Trúc Thư Mục Dự Kiến

```text
.
├── data/               # Các file dữ liệu test input (.json / .txt)
├── src/
│   ├── models.py       # Khai báo Data Classes (Node, Request, Route, Taxi)
│   ├── checker.py      # Hàm kiểm tra ràng buộc cứng & tính Benefit
│   ├── greedy.py       # Thuật toán khởi tạo nghiệm ban đầu
│   ├── operators.py    # Các toán tử Destroy & Repair / Local Search
│   └── alns.py         # Bộ giải ALNS chính
├── main.py             # Entry point nhận input, chạy solver và xuất output
├── requirements.txt    # Danh sách thư viện cần thiết
└── README.md           # Tài liệu hướng dẫn dự án
