from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Node:
    """Đại diện cho một điểm trên bản đồ (v_r^k)"""
    id: int                # ID duy nhất của Node
    type: str              # Loại điểm: 'depot', 'passenger_pickup', 'passenger_dropoff', 'parcel_pickup', 'parcel_dropoff'
    matrix_index: int      # Chỉ số (index) dùng để tra cứu t(u, v) và c(u, v) trong ma trận thời gian/chi phí

@dataclass
class PassengerRequest:
    """Yêu cầu Hành khách i (1 <= i <= N)"""
    id: int                # Mã yêu cầu khách (i)
    pickup_node: Node      # Điểm đón khách (P_i^n)
    dropoff_node: Node     # Điểm trả khách (D_i^n)
    revenue: float         # Doanh thu (T_i^n)
    early_pickup: float    # Thời gian đón sớm nhất (E_i^n)
    late_pickup: float     # Thời gian đón muộn nhất (L_i^n)
    service_time: float    # Thời gian phục vụ đón/trả (S_i^n)

@dataclass
class ParcelRequest:
    """Yêu cầu Bưu kiện j (1 <= j <= M)"""
    id: int                # Mã yêu cầu bưu kiện (j)
    pickup_node: Node      # Điểm nhận hàng (P_j^h)
    dropoff_node: Node     # Điểm giao hàng (D_j^h)
    revenue: float         # Doanh thu (T_j^h)
    early_pickup: float    # Lấy hàng sớm nhất (E_j^{h,p})
    late_pickup: float     # Lấy hàng muộn nhất (L_j^{h,p})
    early_dropoff: float   # Giao hàng sớm nhất (E_j^{h,d})
    late_dropoff: float    # Giao hàng muộn nhất (L_j^{h,d})
    service_time: float    # Thời gian phục vụ lấy/giao (S_j^h)
    weight: float          # Khối lượng bưu kiện (w_j)

@dataclass
class Taxi:
    """Thông tin xe Taxi k (1 <= k <= K)"""
    id: int                # Mã số xe (k)
    depot_node: Node       # Điểm xuất phát ban đầu (O_k)
    capacity: float        # Sức chứa bưu kiện tối đa (Q_k)

@dataclass
class Route:
    """Lộ trình R_k của một taxi k"""
    taxi: Taxi             # Xe taxi thực hiện lộ trình này
    stops: List[Node] = field(default_factory=list) # Chuỗi các điểm dừng (v_0^k, v_1^k, ..., v_{m_k}^k)
    
    # Các thuộc tính theo dõi trạng thái hiện tại (cập nhật dần qua checker)
    current_load: float = 0.0      # Tải trọng bưu kiện hiện tại (load_k <= Q_k)
    current_time: float = 0.0      # Thời gian hiện tại của xe
    total_cost: float = 0.0        # Tổng chi phí di chuyển