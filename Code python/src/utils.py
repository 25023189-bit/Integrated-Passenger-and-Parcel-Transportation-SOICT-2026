from typing import Optional, Tuple
import math
from typing import Tuple

def calculate_next_time(
    dep_u: float,
    u_idx: int,
    v_idx: int,
    time_matrix: list,
    early_v: float,
    late_v: float,
    service_v: float
) -> Optional[Tuple[float, float, float]]:
    """
    Tính toán luồng thời gian từ điểm u sang điểm v theo đúng công thức (2), (3), (4).
    Trả về None nếu vi phạm ràng buộc cứng (đến muộn hơn late_v).
    """
    # [Công thức 2]: arr_v = dep_u + t(u, v)
    arr_v = dep_u + time_matrix[u_idx][v_idx]  # Tải trực tiếp từ ma trận thời gian t(u,v)

    # [Kiểm tra ràng buộc cứng L_v]: ngắt sớm (Early Exit) nếu đến muộn hơn khung thời gian cho phép
    if arr_v > late_v:
        return None  # Trả về None ngay lập tức, ngắt sớm vòng lặp để tối ưu TLE trong ALNS

    # [Công thức 3]: srv_v = max(arr_v, E_v)
    # Tối ưu: Dùng ternary operator thay cho hàm max() của Python giúp chạy nhanh gấp 2-3 lần trong loop lớn
    srv_v = arr_v if arr_v >= early_v else early_v  # Nếu đến sớm hơn E_v thì xe phải chờ đến E_v

    # [Công thức 4]: dep_v = srv_v + S_v
    dep_v = srv_v + service_v  # Thời điểm rời điểm v sau khi làm xong dịch vụ

    # Trả về đủ 3 mốc: thời điểm đến, thời điểm bắt đầu phục vụ, thời điểm rời đi
    # (dep_v chính là dep_u của bước tiếp theo khi lặp qua node kế tiếp)
    return arr_v, srv_v, dep_v


def get_spatial_transition(
    u_idx: int,
    v_idx: int,
    cost_matrix: list,
    time_matrix: list
) -> Tuple[float, float]:
    """
    Tra cứu chi phí c(u, v) và thời gian t(u, v) chuyển vùng giữa 2 nút không gian liên tiếp.
    """
    # [Tối ưu tốc độ]: Tra cứu trực tiếp trên ma trận 2 chiều O(1)
    cost = cost_matrix[u_idx][v_idx]
    travel_time = time_matrix[u_idx][v_idx]

    # Lý do làm vậy: Ngắt sớm nếu ma trận báo đường đi không hợp lệ (vô cực)
    # (dùng để đánh dấu 2 node không có đường nối trực tiếp, nếu đề bài có yêu cầu đó)
    if math.isinf(cost) or math.isinf(travel_time):
        return float('inf'), float('inf')

    return cost, travel_time


def calculate_next_load(
    current_load: float,
    node_type: str,
    weight: float,
    capacity: float
) -> Optional[float]:
    """
    Tính toán luồng tải trọng theo Công thức (5) và kiểm tra sức chứa Q_k theo Công thức (6).
    Trả về None nếu vi phạm (vượt capacity hoặc tải âm).
    """
    # [Công thức 5]: Cập nhật tải trọng dựa trên loại nút dịch vụ
    if node_type == 'PARCEL_PICKUP':
        new_load = current_load + weight  # Lấy hàng: load_v = load_u + w_j
    elif node_type == 'PARCEL_DROPOFF':
        new_load = current_load - weight  # Giao hàng: load_v = load_u - w_j
    else:
        # Lý do: Sự có mặt của hành khách KHÔNG tính vào sức chứa bưu kiện Q_k (đề bài mục 1.4)
        # -> node là điểm đón/trả khách thì tải trọng không đổi, trả về nguyên current_load
        return current_load

    # [Công thức 6]: Kiểm tra ràng buộc 0 <= load_v <= Q_k
    # Lý do ngắt sớm (Early Exit): Nếu vượt quá sức chứa Q_k hoặc âm tải trọng, loại bỏ ngay lập tức
    if new_load > capacity or new_load < -1e-9:
        return None  # Trả về None để các thuật toán ALNS / Greedy loại bỏ chèn không hợp lệ

    # Lý do: Dùng max(0.0, ...) để triệt tiêu sai số làm tròn số thực (float precision error) của Python
    return max(0.0, new_load)