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