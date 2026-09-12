**Tuần 1 (20/09 - 27/09): Nền Tảng & Lời Giải Cơ Sở**
- [ ] Xây dựng các lớp/cấu trúc dữ liệu trong Python (Node, Request, Route, State).
- [ ] Viết hàm kiểm tra tính hợp lệ của lộ trình (Checker/Validator).
- [ ] Hiện thực thuật toán Greedy Insertion để tạo lời giải ban đầu hợp lệ có lợi nhuận dương.
- [ ] *Dự phòng:* Viết thuật toán Random Insertion kèm cơ chế bỏ qua đơn vi phạm phòng trường hợp Greedy không chèn được đơn.

**Tuần 2 (28/09 - 04/10): Tối Ưu Cục Bộ (Local Search)**
- [ ] Phát triển các toán tử di chuyển điểm: Relocate, Swap, 2-opt.
- [ ] Kết hợp các toán tử với thuật toán Hill Climbing để cải thiện điểm số.
- [ ] *Dự phòng:* Tách riêng 2 tập toán tử cho khách và bưu kiện nếu hàm Swap làm hỏng tính chất "chở khách đi thẳng".

**Tuần 3 (05/10 - 12/10): Tích Hợp ALNS (Thuật toán lõi)**
- [ ] Xây dựng các hàm phá hủy lộ trình (Random Destroy, Worst Cost Destroy, Shaw Destroy).
- [ ] Xây dựng các hàm sửa chữa lộ trình (Greedy Repair, Regret Insertion).
- [ ] Cài đặt cơ chế cập nhật trọng số toán tử động dựa trên điểm số thu được.
- [ ] *Dự phòng:* Chuyển sang dùng Simulated Annealing chạy trên nền Local Search nếu ALNS sinh quá nhiều lỗi hoặc không hội tụ.

**Tuần 4 (13/10 - 20/10): Tinh Chỉnh & Tối Ưu Tốc Độ**
- [ ] Tinh chỉnh tham số thuật toán (nhiệt độ SA, hệ số thưởng ALNS).
- [ ] Tối ưu hóa hiệu năng code (sử dụng PyPy, vectorized numpy, hoặc cache tính toán khoảng cách).
- [ ] *Dự phòng (Chống TLE):* Thiết lập cơ chế ngắt thời gian cứng (timeout guard) để dừng vòng lặp và in kết quả tốt nhất khi sắp hết giờ.
