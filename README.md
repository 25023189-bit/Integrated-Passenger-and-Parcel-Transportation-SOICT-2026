## Cấu Trúc Thư Mục Dự Án

```text
.
├── data/               # Chứa các file dữ liệu test đầu vào (.json / .txt).
│
├── src/                # Thư mục chứa mã nguồn cốt lõi.
│   ├── models.py       # Định nghĩa các Class đối tượng (Node, Request, Route, Taxi).
│   ├── checker.py      # Kiểm tra tính hợp lệ của lộ trình và tính điểm Benefit.
│   ├── greedy.py       # Thuật toán sinh lời giải cơ sở ban đầu (Baseline).
│   ├── operators.py    # Các toán tử phá hủy/sửa chữa lộ trình (Destroy, Repair, Local Search).
│   └── alns.py         # Logic chính điều phối thuật toán ALNS.
│
├── main.py             # File chạy chính: Đọc dữ liệu, gọi solver và in kết quả cuối cùng.
├── requirements.txt    # Danh sách các thư viện Python cần cài đặt.
└── README.md           # Tài liệu mô tả dự án và hướng dẫn chạy code.
```

---

## Quy Ước Đặt Tên Biến

Để dễ dàng theo dõi và đối chiếu mã nguồn với mô hình toán học của đề bài, dự án tuân thủ quy tắc ánh xạ biến như sau:

### 1. Yêu cầu Hành khách (Passenger)
| Ký hiệu Toán học | Tên biến trong Python (`PassengerRequest`) | Ý nghĩa |
| :--- | :--- | :--- |
| $i$ | `id` | Mã số yêu cầu hành khách |
| $P_i^n$ / $D_i^n$ | `pickup_node` / `dropoff_node` | Điểm đón / Điểm trả khách |
| $T_i^n$ | `revenue` | Doanh thu thu được |
| $[E_i^n, L_i^n]$ | `early_pickup` / `late_pickup` | Khung thời gian đón khách |
| $S_i^n$ | `service_time` | Thời gian thực hiện đón/trả |

### 2. Yêu cầu Bưu kiện (Parcel)
| Ký hiệu Toán học | Tên biến trong Python (`ParcelRequest`) | Ý nghĩa |
| :--- | :--- | :--- |
| $j$ | `id` | Mã số yêu cầu bưu kiện |
| $P_j^h$ / $D_j^h$ | `pickup_node` / `dropoff_node` | Điểm nhận / Điểm giao hàng |
| $T_j^h$ | `revenue` | Doanh thu thu được |
| $[E_j^{h,p}, L_j^{h,p}]$ | `early_pickup` / `late_pickup` | Khung thời gian lấy hàng |
| $[E_j^{h,d}, L_j^{h,d}]$ | `early_dropoff` / `late_dropoff` | Khung thời gian giao hàng |
| $S_j^h$ | `service_time` | Thời gian bốc dỡ hàng |
| $w_j$ | `weight` | Khối lượng kiện hàng |

### 3. Xe Taxi & Lộ trình
| Ký hiệu Toán học | Tên biến trong Python (`Taxi` / `Route`) | Ý nghĩa |
| :--- | :--- | :--- |
| $k$ | `Taxi.id` | Mã số định danh xe Taxi |
| $O_k$ | `Taxi.depot_node` | Điểm xuất phát ban đầu lúc $t=0$ |
| $Q_k$ | `Taxi.capacity` | Sức chứa bưu kiện tối đa |
| $R_k$ | `Route.stops` | Danh sách các điểm dừng đã lên lịch |
| $load_k$ | `Route.current_load` | Tổng khối lượng bưu kiện đang chở |
| $t(u, v)$ | `time_matrix[u][v]` | Ma trận thời gian di chuyển |
| $c(u, v)$ | `cost_matrix[u][v]` | Ma trận chi phí di chuyển |
