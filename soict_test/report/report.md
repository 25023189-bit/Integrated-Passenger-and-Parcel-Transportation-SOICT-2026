# Báo cáo bộ test cực đoan + test lớn

- Thời điểm: 2026-10-05 00:25 | Solution: `Code python/solution.py` | SOICT_TL: 20 s
- Số test: 30 | OK: 30 | Lỗi: 0

- RAM đỉnh lớn nhất: **425.4 MB** (test `huge`, V=1400)
  - 6 test vượt 256 MB
  - 0 test vượt 512 MB
  - 0 test vượt 1024 MB
- Thời gian lớn nhất: **24.1 s** (test `big_normal`)

| Test | K | N | M | V | Điểm | Thời gian (s) | RAM đỉnh (MB) | Trạng thái | Ghi chú |
|---|--:|--:|--:|--:|--:|--:|--:|:-:|---|
| no_requests | 3 | 0 | 0 | 3 | 0 | 0.18 | 15.6 | OK | N=M=0 (ngoài đặc tả, kiểm tra không crash) |
| k1_small | 1 | 8 | 8 | 33 | 448 | 0.13 | 15.5 | OK | K=1, nhỏ |
| only_parcel_mid | 5 | 0 | 40 | 85 | 3064 | 0.31 | 16.3 | OK | toàn bưu kiện (N=0) |
| only_pass_mid | 5 | 40 | 0 | 85 | 2398 | 0.28 | 16.2 | OK | toàn khách (M=0) |
| zero_dist | 5 | 40 | 40 | 165 | 22441 | 21.00 | 19.1 | OK | mọi khoảng cách = 0: đáp án = tổng doanh thu |
| cap_too_small | 10 | 40 | 40 | 170 | 4763 | 7.70 | 21.0 | OK | mọi bưu kiện nặng hơn sức chứa: chỉ còn khách |
| asym_mid | 10 | 50 | 50 | 210 | 6157 | 11.94 | 24.0 | OK | T, C bất đối xứng, C độc lập với T, vi phạm bất đẳng thức tam giác |
| huge_revenue | 10 | 50 | 50 | 210 | 2.46474e+08 | 11.00 | 24.3 | OK | doanh thu rất lớn: phục vụ tối đa |
| infeasible_all | 10 | 50 | 50 | 210 | 0 | 0.26 | 23.6 | OK | mọi cửa sổ không với tới được: đáp án = 0 |
| no_profit_mid | 10 | 50 | 50 | 210 | 0 | 0.61 | 24.0 | OK | không đơn nào có lời: đáp án đúng = 0 |
| win_point_mid | 10 | 50 | 50 | 210 | 5002 | 8.05 | 23.7 | OK | E = L (cửa sổ độ rộng 0) |
| win_tight_mid | 10 | 50 | 50 | 210 | 5339 | 8.24 | 23.7 | OK | cửa sổ rộng 0-2, neo theo khoảng cách từ depot |
| win_wide_mid | 10 | 50 | 50 | 210 | 19546 | 21.22 | 40.1 | OK | L = 100000 |
| cap_equal | 10 | 30 | 80 | 230 | 7143 | 9.84 | 27.3 | OK | w = Q: mỗi lần chở đúng 1 bưu kiện |
| k1_mid | 1 | 60 | 60 | 241 | 1021 | 0.65 | 28.6 | OK | K=1, một xe phải chọn đơn |
| long_service | 10 | 60 | 60 | 250 | 4229 | 0.60 | 28.5 | OK | thời gian phục vụ dài |
| many_vehicles | 300 | 10 | 10 | 340 | 3782 | 20.43 | 39.0 | OK | xe nhiều hơn yêu cầu |
| cap_one | 20 | 20 | 150 | 360 | 11427 | 20.35 | 42.0 | OK | Q=1 |
| win_wide_k1 | 1 | 100 | 100 | 401 | 38430 | 21.27 | 47.0 | OK | 1 xe, cửa sổ rất rộng: route rất dài |
| dense_peak | 20 | 150 | 150 | 620 | 15927 | 14.92 | 95.0 | OK | mọi E trong [0,10]: tranh chấp tài nguyên cao |
| only_parcel_big | 60 | 0 | 300 | 660 | 44032 | 21.50 | 104.9 | OK | toàn bưu kiện, M=300 |
| only_pass_big | 60 | 300 | 0 | 660 | 32932 | 24.02 | 106.9 | OK | toàn khách, N=300 |
| real_like_xl | 30 | 250 | 250 | 1030 | 31342 | 22.98 | 228.8 | OK | giống test thật nhưng lớn hơn |
| asym_big | 80 | 250 | 250 | 1080 | 47318 | 22.36 | 250.1 | OK |  |
| k1_big | 1 | 300 | 300 | 1201 | 1463 | 21.01 | 312.7 | OK | K=1, 600 yêu cầu |
| big_normal | 100 | 300 | 300 | 1300 | 78645 | 24.05 | 356.2 | OK | K,N,M hàng trăm, cửa sổ như test thật |
| no_profit_big | 100 | 300 | 300 | 1300 | 0 | 21.70 | 357.0 | OK |  |
| win_tight_big | 100 | 300 | 300 | 1300 | 51661 | 23.57 | 358.2 | OK |  |
| win_wide_big | 100 | 300 | 300 | 1300 | 106884 | 22.48 | 356.1 | OK | cửa sổ rất rộng: không gian tìm kiếm lớn nhất |
| huge | 200 | 300 | 300 | 1400 | 110194 | 23.44 | 425.4 | OK | V=1400: kiểm tra RAM/thời gian đọc input |

> Lưu ý: ở TL ngắn, RAM thật có thể bị đánh giá thấp vì ALNS/exact_solve (`build_pool` tới 6.000.000 trạng thái) còn chạy tiếp. Chạy `--full --only big` ít nhất một lần để lấy RAM đỉnh thật.
