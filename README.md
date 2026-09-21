# README - TUẦN 1: LOCAL SEARCH & DELTA EVALUATION

**Thời gian:** 21/09/2026 – 26/09/2026  
**Mục tiêu:** Cải thiện kết quả từ Greedy Solver bằng thuật toán Tìm kiếm cục bộ (Local Search) kết hợp tính toán chênh lệch chi phí Delta O(1).

---

## 1. Phân Công Nhiệm Vụ

### Hà Thu (Nhánh 1: Cấu trúc & Toán tử)
* **File làm việc:** `operators.py`
* **Nhiệm vụ:**
  * Code toán tử `relocate(route, node_idx, target_idx)` và `swap(route1, route2, node_idx1, node_idx2)`.
  * Đảm bảo **Pair Mode**: Khi di chuyển đơn khách, luôn đi liền cặp `[Pickup, Dropoff]`.
  * Phân loại toán tử nội bộ 1 xe (`intra_route`) và giữa các xe (`inter_route`).

### Dũng (Nhánh 2: Tối ưu & Thuật toán)
* **File làm việc:** `evaluator.py`, `hill_climbing.py`
* **Nhiệm vụ:**
  * Code hàm `calculate_delta_cost(...)` tính chênh lệch chi phí O(1).
  * Code hàm `calculate_delta_time(...)` và `check_capacity_delta(...)` để ngắt sớm khi vi phạm.
  * Xây dựng lớp `HillClimbingSolver` điều phối vòng lặp Local Search.

--

## 2. Nguyên Tắc Làm Việc Song Song

1. **Giao tiếp qua Interface:** Thống nhất trước tên hàm và tham số truyền vào, không ngồi chờ nhau.
2. **Độc lập File:** 
   * Hà Thu chỉ sửa `operators.py`.
   * Dũng chỉ sửa `evaluator.py` và `hill_climbing.py`.
   * Không tự ý thay đổi `models.py` hoặc `validator.py`.
3. **Test độc lập:**
   * Hà Thu dùng `validator.py` cũ để kiểm tra logic mảng.
   * Dũng dùng dữ liệu giả lập để kiểm tra vòng lặp Hill Climbing.
4. **Quy trình ghép code:** Dũng import `operators.py` vào `hill_climbing.py` và chạy test tổng thể trên `main.py`.
