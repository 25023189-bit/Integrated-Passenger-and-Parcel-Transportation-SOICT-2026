"""
Bài toán Taxi vận chuyển Khách + Bưu kiện - bản GỘP 1 FILE để nộp bài.
Gộp từ: models, utils, validator, evaluator, greedy_solver, random_solver,
        operators, hill_climbing, main.
Chạy:  python solution.py
"""
import copy
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


# ======================================================================
# models.py
# ======================================================================

# Kkhai báo toàn bộ cấu trúc dữ liệu (data model) của bài toán
# Mỗi class tương ứng với 1 ký hiệu toán học trong đề bài

@dataclass(unsafe_hash=True)
class Node:
    """Đại diện cho một điểm trên bản đồ (v_r^k)"""
    id: int               # id duy nhất của node, dùng để in/so sánh cho dễ đọc
    type: str             # loại node: 'DEPOT', 'PASSENGER_PICKUP', 'PASSENGER_DROPOFF', 'PARCEL_PICKUP', 'PARCEL_DROPOFF'
    matrix_index: int     # chỉ số hàng/cột tương ứng của node này trong ma trận time/cost  
    
@dataclass(unsafe_hash=True)
class PassengerRequest:
    """Yêu cầu Hành khách i (1 <= i <= N)"""
    id: int               # id của yêu cầu khách (khác với id của Node)
    pickup_node: Node      # P_i^n: điểm đón khách
    dropoff_node: Node     # D_i^n: điểm trả khách
    revenue: float         # T_i^n: doanh thu nếu phục vụ được khách này
    early_pickup: float    # E_i^n: thời điểm sớm nhất được phép đón
    late_pickup: float     # L_i^n: thời điểm muộn nhất được phép đón (quá -> vi phạm cứng)
    service_time: float    # S_i^n: thời gian phục vụ tại MỖI điểm đón/trả (dùng chung cho cả 2)    

@dataclass(unsafe_hash=True)
class ParcelRequest:
    """Yêu cầu Bưu kiện j (1 <= j <= M)"""
    id: int               # id của yêu cầu bưu kiện
    pickup_node: Node      # P_j^h: điểm lấy hàng
    dropoff_node: Node     # D_j^h: điểm giao hàng
    revenue: float         # T_j^h: doanh thu nếu phục vụ được đơn hàng này
    early_pickup: float    # E_j^{h,p}: sớm nhất được lấy hàng
    late_pickup: float     # L_j^{h,p}: muộn nhất được lấy hàng
    early_dropoff: float   # E_j^{h,d}: sớm nhất được giao hàng
    late_dropoff: float    # L_j^{h,d}: muộn nhất được giao hàng
    service_time: float    # S_j^h: thời gian phục vụ tại mỗi điểm lấy/giao
    weight: float          # w_j: khối lượng bưu kiện, dùng để kiểm tra sức chứa xe (Công thức 5, 6)         

@dataclass
class Taxi:
    """Thông tin xe Taxi k (1 <= k <= K)"""
    id: int               # id của xe
    depot_node: Node       # O_k: điểm xuất phát ban đầu của xe (mọi xe thường dùng chung 1 depot)
    capacity: float        # Q_k: sức chứa bưu kiện tối đa của xe (KHÔNG tính chỗ ngồi hành khách)      

@dataclass
class Route:
    """Lộ trình R_k của một taxi k"""
    taxi: Taxi                      # xe nào đảm nhận lộ trình này
    stops: List[Node] = field(default_factory=list)
    # ^ R_k: danh sách các điểm dừng theo đúng thứ tự xe sẽ đi qua (không tính depot ở đầu)
 
    # 3 trường dưới đây được khai báo sẵn để lưu trạng thái, nhưng trong code hiện tại
    # (validator.py, greedy_solver.py) các hàm tự tính current_time/current_load bằng
    # biến cục bộ trong vòng lặp, KHÔNG ghi ngược lại vào các trường này của Route.
    current_load: float = 0.0     # tải trọng bưu kiện hiện tại trên xe (load_k)
    current_time: float = 0.0     # mốc thời gian hiện tại của xe
    total_cost: float = 0.0       # tổng chi phí di chuyển đã tích lũy     

@dataclass
class ProblemInstance:
    """Lưu trữ toàn bộ dữ liệu của một testcase"""
    taxis: List[Taxi]
    passengers: List[PassengerRequest]
    parcels: List[ParcelRequest]
    time_matrix: List[List[float]]   # t(u, v): thời gian di chuyển giữa mọi cặp node
    cost_matrix: List[List[float]]   # c(u, v): chi phí di chuyển giữa mọi cặp node
 
    # 2 dict tra cứu ngầm (không truyền vào khi khởi tạo, init=False),
    # được tự động build trong __post_init__ ngay sau khi ProblemInstance được tạo.
    # Mục đích: tra "node này thuộc yêu cầu nào" trong O(1) thay vì phải duyệt
    # tuyến tính qua danh sách passengers/parcels mỗi lần cần biết.
    _node_to_passenger: Dict[int, PassengerRequest] = field(default_factory=dict, init=False)
    _node_to_parcel: Dict[int, ParcelRequest] = field(default_factory=dict, init=False)

    def __post_init__(self):
        # Với mỗi hành khách, ánh xạ cả 2 node (pickup và dropoff) của họ về cùng 1 request
        # -> khi gặp bất kỳ node nào trong 2 node đó, ta đều tra ra được đúng PassengerRequest
        for p in self.passengers:
            self._node_to_passenger[p.pickup_node.matrix_index] = p
            self._node_to_passenger[p.dropoff_node.matrix_index] = p
        # Tương tự cho bưu kiện
        for h in self.parcels:
            self._node_to_parcel[h.pickup_node.matrix_index] = h
            self._node_to_parcel[h.dropoff_node.matrix_index] = h
 
    def get_passenger_by_node(self, node: Node) -> Optional[PassengerRequest]:
        # Tra cứu O(1) bằng matrix_index; trả về None nếu node không thuộc khách nào
        return self._node_to_passenger.get(node.matrix_index)
 
    def get_parcel_by_node(self, node: Node) -> Optional[ParcelRequest]:
        return self._node_to_parcel.get(node.matrix_index)
 
    def get_node_time_windows(self, node: Node) -> Tuple[float, float, float]:
        """Trả về (early, late, service_time) tương ứng với node được truyền vào,
        bất kể node đó là của hành khách hay bưu kiện, pickup hay dropoff."""
        pass_req = self.get_passenger_by_node(node)
        if pass_req:
            # Hành khách chỉ có 1 cặp early/late dùng chung cho cả pickup lẫn dropoff
            return pass_req.early_pickup, pass_req.late_pickup, pass_req.service_time
 
        parcel_req = self.get_parcel_by_node(node)
        if parcel_req:
            # Bưu kiện có 2 cặp early/late riêng cho pickup và dropoff -> phải phân biệt qua node.type
            if node.type == 'PARCEL_PICKUP':
                return parcel_req.early_pickup, parcel_req.late_pickup, parcel_req.service_time
            elif node.type == 'PARCEL_DROPOFF':
                return parcel_req.early_dropoff, parcel_req.late_dropoff, parcel_req.service_time
 
        # Trường hợp node không khớp yêu cầu nào (ví dụ Depot) -> không ràng buộc thời gian
        return 0.0, float('inf'), 0.0


# ======================================================================
# utils.py
# ======================================================================

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


# ======================================================================
# validator.py
# ======================================================================

# Chứa các hàm kiểm tra tính hợp lệ của 1 lộ trình (Route), bao gồm 4 loại Bảo toàn luồng
# Có 2 nhóm hàm:
#   - 4 hàm validate_* riêng lẻ: mỗi hàm chỉ kiểm tra 1 điều kiện
#   - is_route_valid(): gộp cả 4 điều kiện vào 1 vòng lặp duy nhất, tối ưu tốc độ,
#     đây là hàm thực sự được gọi trong vòng lặp của greedy_solver.py / random_solver.py

def validate_temporal_flow(route: Route, instance: ProblemInstance) -> bool:
    """Kiểm tra riêng điều kiện Bảo toàn luồng Thời gian (Công thức 2, 3, 4)."""
    stops = route.stops
    if not stops:
        return True  # Lộ trình rỗng thì mặc nhiên hợp lệ

    dep_u = 0.0  # Giả định xe rời Depot lúc thời điểm t = 0
    u_idx = route.taxi.depot_node.matrix_index
    time_matrix = instance.time_matrix

    # Duyệt tuần tự từng điểm dừng, tích lũy mốc thời gian departure của điểm trước
    # để tính arrival của điểm sau -> đúng bản chất "luồng" (giá trị sau phụ thuộc giá trị trước)
    for node in stops:
        v_idx = node.matrix_index
        early_v, late_v, service_v = instance.get_node_time_windows(node)

        arr_v = dep_u + time_matrix[u_idx][v_idx]  # Công thức (2)

        if arr_v > late_v:
            return False  # Đến muộn hơn cửa sổ cho phép -> vi phạm cứng, dừng ngay

        srv_v = arr_v if arr_v >= early_v else early_v  # Công thức (3): chờ nếu đến sớm
        dep_u = srv_v + service_v                       # Công thức (4), gán lại làm dep_u cho vòng lặp kế tiếp
        u_idx = v_idx                                   # Node hiện tại trở thành "u" của bước kế tiếp

    return True


def validate_spatial_flow(route: Route, instance: ProblemInstance) -> bool:
    """Kiểm tra riêng điều kiện Bảo toàn luồng Không gian (Công thức 1)."""
    stops = route.stops
    if not stops:
        return True

    cost_matrix = instance.cost_matrix
    time_matrix = instance.time_matrix
    num_nodes = len(cost_matrix)

    depot_node = route.taxi.depot_node
    first_node = stops[0]

    u_idx = depot_node.matrix_index
    v_idx = first_node.matrix_index

    # Kiểm tra cạnh Depot -> điểm dừng đầu tiên có hợp lệ không
    if not (0 <= u_idx < num_nodes and 0 <= v_idx < num_nodes):
        return False  # index vượt ngoài kích thước ma trận -> dữ liệu sai

    if math.isinf(cost_matrix[u_idx][v_idx]) or math.isinf(time_matrix[u_idx][v_idx]):
        return False  # Cạnh bị đánh dấu vô cực -> không có đường đi thực tế giữa 2 node này

    # Kiểm tra tiếp từng cạnh liên tiếp giữa các điểm dừng: stops[i] -> stops[i+1]
    for i in range(len(stops) - 1):
        curr_idx = stops[i].matrix_index
        next_idx = stops[i + 1].matrix_index

        if not (0 <= curr_idx < num_nodes and 0 <= next_idx < num_nodes):
            return False

        if math.isinf(cost_matrix[curr_idx][next_idx]) or math.isinf(time_matrix[curr_idx][next_idx]):
            return False

    return True


def validate_capacity_flow(route: Route, instance: ProblemInstance) -> bool:
    """Kiểm tra riêng điều kiện Bảo toàn luồng Tải trọng (Công thức 5, 6)."""
    stops = route.stops
    if not stops:
        return True

    capacity = route.taxi.capacity
    current_load = 0.0  # Xe xuất phát với tải trọng bằng 0

    for node in stops:
        if node.type == 'PARCEL_PICKUP':
            parcel = instance.get_parcel_by_node(node)
            if parcel is None:
                return False  # Node được gán loại PARCEL_PICKUP nhưng không tra ra request -> dữ liệu lỗi

            current_load += parcel.weight  # Công thức (5): lấy hàng thì cộng tải
            if current_load > capacity:
                return False  # Vượt sức chứa Q_k -> vi phạm Công thức (6)

        elif node.type == 'PARCEL_DROPOFF':
            parcel = instance.get_parcel_by_node(node)
            if parcel is None:
                return False

            current_load -= parcel.weight  # Công thức (5): giao hàng thì trừ tải
            if current_load < -1e-7:
                # Tải âm nghĩa là giao 1 món hàng chưa từng được lấy trước đó trong route này
                # (dùng ngưỡng -1e-7 thay vì so sánh == 0 để tránh sai số dấu phẩy động)
                return False

    # Kết thúc lộ trình mà tải trọng vẫn còn dư (>0) -> có hàng đã lấy nhưng chưa giao hết
    if current_load > 1e-7:
        return False

    return True


def validate_direct_passenger_flow(route: Route, instance: ProblemInstance) -> bool:
    """Kiểm tra riêng điều kiện Bảo toàn luồng Trực tiếp Hành khách (Công thức 7)."""
    stops = route.stops
    if not stops:
        return True

    n_stops = len(stops)
    for i, node in enumerate(stops):
        if node.type == 'PASSENGER_PICKUP':
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None:
                return False

            # Ràng buộc cốt lõi: ngay SAU điểm đón khách phải LẬP TỨC là điểm trả khách đó,
            # không được có bất kỳ node nào khác chen giữa
            if i + 1 >= n_stops:
                return False  # Đón khách nhưng đây lại là điểm dừng cuối cùng -> không có chỗ trả khách

            next_node = stops[i + 1]
            if next_node.id != passenger_req.dropoff_node.id:
                return False  # Điểm ngay sau không phải đúng điểm trả của khách này -> vi phạm

        elif node.type == 'PASSENGER_DROPOFF':
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None:
                return False

            # Kiểm tra chiều ngược lại: điểm trả khách phải có điểm đón NGAY TRƯỚC nó
            if i == 0:
                return False  # Trả khách nhưng lại là điểm dừng đầu tiên -> không hợp lý (chưa từng đón)

            prev_node = stops[i - 1]
            if prev_node.id != passenger_req.pickup_node.id:
                return False

    return True


def validate_time_windows_and_precedence(route: Route, instance: ProblemInstance) -> bool:
    """
    Phiên bản kiểm tra thời gian CHI TIẾT hơn validate_temporal_flow: xử lý riêng
    từng loại node (khách/hàng, pickup/dropoff) và thêm kiểm tra thứ tự lấy-trước-giao-sau
    cho bưu kiện (picked_up_parcels). Không được gọi trong is_route_valid, nhưng hữu ích
    để hiểu rõ luồng thời gian + logic "phải lấy hàng trước khi giao" tách biệt.
    """
    stops = route.stops
    if not stops:
        return True

    current_time = 0.0
    current_node = route.taxi.depot_node
    picked_up_parcels = set()  # Ghi nhớ các bưu kiện đã được lấy nhưng chưa giao

    for node in stops:
        travel_time = instance.time_matrix[current_node.matrix_index][node.matrix_index]
        arrival_time = current_time + travel_time

        if node.type == 'PASSENGER_PICKUP':
            req = instance.get_passenger_by_node(node)
            if req is None or arrival_time > req.late_pickup:
                return False
            start_service = max(arrival_time, req.early_pickup)
            departure_time = start_service + req.service_time

        elif node.type == 'PASSENGER_DROPOFF':
            req = instance.get_passenger_by_node(node)
            if req is None:
                return False
            # Trả khách không có ràng buộc "trễ" riêng (không có late_dropoff cho khách) -> luôn chấp nhận arrival
            start_service = arrival_time
            departure_time = start_service + req.service_time

        elif node.type == 'PARCEL_PICKUP':
            req = instance.get_parcel_by_node(node)
            if req is None or arrival_time > req.late_pickup:
                return False
            start_service = max(arrival_time, req.early_pickup)
            departure_time = start_service + req.service_time
            picked_up_parcels.add(req.id)  # Đánh dấu đã lấy hàng này

        elif node.type == 'PARCEL_DROPOFF':
            req = instance.get_parcel_by_node(node)
            # Phải đã lấy hàng này trước đó (req.id in picked_up_parcels) mới được giao
            if req is None or req.id not in picked_up_parcels:
                return False
            if arrival_time > req.late_dropoff:
                return False
            start_service = max(arrival_time, req.early_dropoff)
            departure_time = start_service + req.service_time

        current_time = departure_time
        current_node = node

    return True


def is_route_valid(route: Route, instance: ProblemInstance) -> bool:
    """
    Hàm tổng hợp kiểm tra nhanh toàn bộ Ràng buộc Cứng bằng 1 vòng lặp O(N) duy nhất.
    Được sử dụng trong các vòng lặp sinh lời giải liên tục để tránh nghẽn TLE.

    Đây là bản "viết gộp lại" của 4 hàm validate_* ở trên, để chỉ phải duyệt qua
    danh sách stops MỘT LẦN thay vì 4 lần (mỗi hàm validate_* riêng lẻ duyệt 1 lần).
    """
    stops = route.stops
    if not stops:
        return True

    time_matrix = instance.time_matrix
    cost_matrix = instance.cost_matrix
    num_nodes = len(cost_matrix)
    capacity = route.taxi.capacity
    n_stops = len(stops)

    # 3 biến trạng thái tích lũy, cùng cập nhật song song trong 1 vòng lặp duy nhất
    current_time = 0.0
    current_load = 0.0
    current_node = route.taxi.depot_node
    picked_up_parcels = set()

    for i, node in enumerate(stops):
        u_idx = current_node.matrix_index
        v_idx = node.matrix_index

        # 1. Luồng không gian: kiểm tra cạnh (u_idx -> v_idx) có hợp lệ không
        if not (0 <= u_idx < num_nodes and 0 <= v_idx < num_nodes):
            return False
        if math.isinf(cost_matrix[u_idx][v_idx]) or math.isinf(time_matrix[u_idx][v_idx]):
            return False

        arrival_time = current_time + time_matrix[u_idx][v_idx]
        node_type = node.type

        # 2. Chi tiết từng ràng buộc theo loại nút
        if node_type == 'PASSENGER_PICKUP':
            req = instance.get_passenger_by_node(node)
            if not req or arrival_time > req.late_pickup:
                return False
            # Luồng khách trực tiếp: node ngay sau BẮT BUỘC là dropoff của chính khách này
            if i + 1 >= n_stops or stops[i + 1].id != req.dropoff_node.id:
                return False
            start_service = arrival_time if arrival_time >= req.early_pickup else req.early_pickup
            current_time = start_service + req.service_time

        elif node_type == 'PASSENGER_DROPOFF':
            req = instance.get_passenger_by_node(node)
            # Kiểm tra chiều ngược: node ngay trước phải là pickup của chính khách này
            if not req or i == 0 or stops[i - 1].id != req.pickup_node.id:
                return False
            current_time = arrival_time + req.service_time

        elif node_type == 'PARCEL_PICKUP':
            req = instance.get_parcel_by_node(node)
            if not req or arrival_time > req.late_pickup:
                return False

            current_load += req.weight
            if current_load > capacity:
                return False  # Vi phạm sức chứa ngay tại thời điểm lấy hàng này

            picked_up_parcels.add(req.id)
            start_service = arrival_time if arrival_time >= req.early_pickup else req.early_pickup
            current_time = start_service + req.service_time

        elif node_type == 'PARCEL_DROPOFF':
            req = instance.get_parcel_by_node(node)
            # Phải: (a) tra được request, (b) đã từng lấy hàng này, (c) không giao muộn
            if not req or req.id not in picked_up_parcels or arrival_time > req.late_dropoff:
                return False

            current_load -= req.weight
            if current_load < -1e-7:
                return False

            picked_up_parcels.remove(req.id)  # Đã giao xong -> bỏ khỏi tập "đang mang trên xe"
            start_service = arrival_time if arrival_time >= req.early_dropoff else req.early_dropoff
            current_time = start_service + req.service_time
        else:
            # Loại node không xác định (không phải 1 trong 4 loại kể trên, và không phải Depot
            # vì Depot không xuất hiện trong stops) -> coi là dữ liệu lỗi
            return False

        current_node = node

    # 3. Bảo toàn cuối chuyến: xe phải "sạch" khi hoàn thành lộ trình
    #    - current_load > 0: còn hàng trên xe chưa giao hết
    #    - len(picked_up_parcels) > 0: còn bưu kiện đã lấy nhưng chưa đánh dấu giao xong
    #    (2 điều kiện này thực chất tương đương nhau, kiểm tra cả 2 cho chắc chắn)
    if current_load > 1e-7 or len(picked_up_parcels) > 0:
        return False

    return True


# ======================================================================
# evaluator.py
# ======================================================================

def calculate_delta_cost(
    node_A: Node,
    node_B: Node,
    insert_node: Node,
    cost_matrix: List[List[float]]
) -> float:
    a_idx = node_A.matrix_index
    b_idx = node_B.matrix_index
    x_idx = insert_node.matrix_index

    cost_AX = cost_matrix[a_idx][x_idx]
    cost_XB = cost_matrix[x_idx][b_idx]
    cost_AB = cost_matrix[a_idx][b_idx]

    return cost_AX + cost_XB - cost_AB


def calculate_delta_time(
    dep_A: float,
    node_A: Node,
    node_B: Node,
    old_dep_B: float,
    insert_node: Node,
    instance: ProblemInstance
) -> Optional[float]:
    t_matrix = instance.time_matrix
    early_X, late_X, service_X = instance.get_node_time_windows(insert_node)
    arr_X = dep_A + t_matrix[node_A.matrix_index][insert_node.matrix_index]
    
    if arr_X > late_X:
        return None

    start_X = arr_X if arr_X >= early_X else early_X
    dep_X = start_X + service_X

    early_B, late_B, service_B = instance.get_node_time_windows(node_B)
    arr_B_new = dep_X + t_matrix[insert_node.matrix_index][node_B.matrix_index]

    if arr_B_new > late_B:
        return None  

    start_B_new = arr_B_new if arr_B_new >= early_B else early_B
    dep_B_new = start_B_new + service_B

    return dep_B_new - old_dep_B


def check_capacity_delta(
    route_stops: List[Node],
    insert_idx: int,
    insert_node: Node,
    capacity: float,
    current_loads: List[float],
    weight: float
) -> bool:
    if insert_node.type in ['PASSENGER_PICKUP', 'PASSENGER_DROPOFF']:
        return True

    if insert_node.type == 'PARCEL_PICKUP':
        for i in range(insert_idx, len(route_stops)):
            if current_loads[i] + weight > capacity:
                return False

    return True


# ======================================================================
# greedy_solver.py
# ======================================================================

# Cài đặt thuật toán GREEDY INSERTION (chèn tham lam): tại mỗi bước, tìm
# phương án chèn 1 đơn (khách hoặc hàng) vào 1 vị trí trên 1 xe sao cho lợi nhuận tăng thêm
# (gain = doanh thu - chi phí phát sinh) là lớn nhất, rồi thực hiện chèn đó.
# Lặp lại cho đến khi không còn phương án nào sinh lời (gain > 0) thì dừng.

class GreedySolver:
    def __init__(self, instance: ProblemInstance):
        self.instance = instance
        # Mỗi xe bắt đầu với 1 Route rỗng (chưa có điểm dừng nào)
        self.routes = [Route(taxi=taxi) for taxi in instance.taxis]

        # Dùng set để tra cứu/xóa phần tử nhanh (O(1)) khi 1 đơn được phục vụ xong
        self.unserved_passengers = set(instance.passengers)
        self.unserved_parcels = set(instance.parcels)

    def get_route_cost(self, route: Route) -> float:
        """Tính tổng chi phí di chuyển thực tế của một lộ trình, TỪ ĐẦU (không dùng delta)."""
        stops = route.stops
        if not stops:
            return 0.0
        cost_mat = self.instance.cost_matrix
        # Cạnh đầu tiên: từ Depot đến điểm dừng đầu tiên
        cost = cost_mat[route.taxi.depot_node.matrix_index][stops[0].matrix_index]
        # Cộng dồn chi phí của từng cạnh liên tiếp giữa các điểm dừng
        for idx in range(len(stops) - 1):
            cost += cost_mat[stops[idx].matrix_index][stops[idx + 1].matrix_index]
        return cost

    def get_passenger_delta_cost(self, route: Route, p_node: Node, d_node: Node, pos: int) -> float:
        """
        [Tối ưu O(1)]: Tính Delta Cost khi chèn liên tiếp [Pickup, Dropoff] của Hành khách vào vị trí pos.

        Ý tưởng: thay vì gọi lại get_route_cost() cho toàn bộ lộ trình mới (tốn O(n)),
        ta chỉ tính PHẦN THAY ĐỔI quanh vị trí chèn: xóa đi 1 cạnh cũ (A -> B), thêm vào
        các cạnh mới (A -> P, P -> D, D -> B). Các cạnh còn lại của lộ trình không đổi
        nên không cần tính lại.
        """
        stops = route.stops
        cost_mat = self.instance.cost_matrix

        # Xác định 2 nút kề bên vị trí chèn: A là nút liền trước, B là nút liền sau
        A = stops[pos - 1] if pos > 0 else route.taxi.depot_node  # Nếu chèn ở đầu thì A = Depot
        B = stops[pos] if pos < len(stops) else None              # Nếu chèn ở cuối thì không có B

        # Tính chi phí cạnh cũ bị xóa (A -> B) và các cạnh mới được thêm vào
        cost_removed = 0.0 if B is None else cost_mat[A.matrix_index][B.matrix_index]
        cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] +
                      cost_mat[p_node.matrix_index][d_node.matrix_index])
        if B is not None:
            cost_added += cost_mat[d_node.matrix_index][B.matrix_index]

        return cost_added - cost_removed  # Delta dương nghĩa là chèn vào làm tăng chi phí

    def get_parcel_delta_cost(self, route: Route, p_node: Node, d_node: Node, i: int, j: int) -> float:
        """
        [Tối ưu O(1)]: Tính Delta Cost khi chèn Pickup tại vị trí i và Dropoff tại vị trí j (trong mảng ban đầu).

        Khác với hành khách, bưu kiện được phép chèn TÁCH RỜI (pickup ở i, dropoff ở j >= i,
        có thể có các điểm dừng khác xen giữa), nên cần xét 2 trường hợp.
        """
        stops = route.stops
        cost_mat = self.instance.cost_matrix

        if i == j:  # Trường hợp chèn liền kề nhau (giống hệt logic hành khách ở trên)
            A = stops[i - 1] if i > 0 else route.taxi.depot_node
            B = stops[i] if i < len(stops) else None

            cost_removed = 0.0 if B is None else cost_mat[A.matrix_index][B.matrix_index]
            cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] +
                          cost_mat[p_node.matrix_index][d_node.matrix_index])
            if B is not None:
                cost_added += cost_mat[d_node.matrix_index][B.matrix_index]
            return cost_added - cost_removed

        else:  # Trường hợp chèn tách rời (i < j) -> có 2 điểm chèn RIÊNG BIỆT, mỗi điểm phá 1 cạnh cũ
            # Tại điểm Pickup (chèn vào vị trí i): A là nút trước, B là nút vốn đang ở vị trí i
            A = stops[i - 1] if i > 0 else route.taxi.depot_node
            B = stops[i]

            # Tại điểm Dropoff (chèn vào vị trí j TRONG MẢNG BAN ĐẦU, tức là trước khi chèn pickup):
            # C là nút liền trước j, D_next là nút liền sau j (nếu có)
            C = stops[j - 1]
            D_next = stops[j] if j < len(stops) else None

            # --- Phần chi phí quanh điểm Pickup: xóa cạnh (A,B), thêm cạnh (A,P) và (P,B) ---
            cost_removed = cost_mat[A.matrix_index][B.matrix_index]
            cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] +
                          cost_mat[p_node.matrix_index][B.matrix_index])

            # --- Phần chi phí quanh điểm Dropoff: xóa cạnh (C, D_next), thêm cạnh (C,D) và (D,D_next) ---
            if D_next is not None:
                cost_removed += cost_mat[C.matrix_index][D_next.matrix_index]
                cost_added += (cost_mat[C.matrix_index][d_node.matrix_index] +
                               cost_mat[d_node.matrix_index][D_next.matrix_index])
            else:
                # j nằm ở cuối lộ trình -> không có cạnh (C, D_next) để xóa, chỉ thêm cạnh (C, D)
                cost_added += cost_mat[C.matrix_index][d_node.matrix_index]

            return cost_added - cost_removed

    def find_best_passenger_insertion(self) -> Tuple[Optional[PassengerRequest], Optional[int], Optional[int], float]:
        """Tìm vị trí chèn hành khách cho lợi nhuận tăng thêm Delta Benefit lớn nhất."""
        # Khởi tạo max_gain = 0.0 nghĩa là: chỉ chấp nhận phương án có lời (gain > 0),
        # nếu không tìm được phương án nào tốt hơn 0 thì trả về best_req = None
        best_req, best_taxi_idx, best_pos, max_gain = None, None, None, 0.0

        # Duyệt qua tất cả tổ hợp: (đơn khách chưa phục vụ) x (mọi xe) x (mọi vị trí chèn)
        for req in self.unserved_passengers:
            nodes = [req.pickup_node, req.dropoff_node]
            for t_idx, route in enumerate(self.routes):
                for i in range(len(route.stops) + 1):  # +1 vì có thể chèn vào SAU điểm dừng cuối
                    # Chèn cặp [Pickup, Dropoff] liền kề để bảo toàn luồng khách đi thẳng (Công thức 7)
                    temp_stops = route.stops[:i] + nodes + route.stops[i:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    # Chỉ xét tiếp nếu lộ trình SAU KHI chèn vẫn thỏa mọi ràng buộc cứng
                    if is_route_valid(temp_route, self.instance):
                        delta_cost = self.get_passenger_delta_cost(route, req.pickup_node, req.dropoff_node, i)
                        gain = req.revenue - delta_cost  # Lợi nhuận tăng thêm = doanh thu - chi phí phát sinh
                        if gain > max_gain:  # Chỉ cập nhật khi tìm được phương án TỐT HƠN phương án đang giữ
                            max_gain = gain
                            best_req, best_taxi_idx, best_pos = req, t_idx, i

        return best_req, best_taxi_idx, best_pos, max_gain

    def find_best_parcel_insertion(self) -> Tuple[Optional[ParcelRequest], Optional[int], Optional[int], Optional[int], float]:
        """
        Tìm vị trí chèn bưu kiện (pickup ở pos_i, dropoff ở pos_j với pos_i <= pos_j)
        cho lợi nhuận tăng thêm Delta Benefit lớn nhất.

        [BẢN TỐI ƯU TỐC ĐỘ] - Vẫn cho ra ĐÚNG kết quả như bản gốc (chỉ khác cách tính),
        vì is_route_valid() thật vẫn được gọi làm bước xác nhận CUỐI CÙNG cho mọi ứng viên
        "có vẻ hợp lệ" - không có ứng viên nào được CHẤP NHẬN mà chưa qua is_route_valid().

        Ý tưởng tối ưu (lý do bản gốc chậm - đã đo bằng cProfile, is_route_valid chiếm ~92%
        thời gian chạy Greedy trên 1 bộ test cỡ Vừa):
          1. Bản gốc: với MỖI request, MỖI xe, MỖI cặp (i, j) trong 2 vòng lặp lồng nhau,
             is_route_valid() phải MÔ PHỎNG LẠI TỪ ĐẦU (từ Depot) toàn bộ route mới ->
             tốn O(n) cho MỖI cặp (i, j), mà số cặp (i, j) là O(n^2) -> O(n^3) cho MỖI
             request trên MỖI xe. Route KHÔNG ĐỔI giữa các request/các cặp (i,j) khác
             nhau, nên phần lớn công tính lại đó là dư thừa.
          2. Ở đây: với mỗi xe, tính 1 LẦN DUY NHẤT (không phải 1 lần/mỗi request) 2 mảng
             dep_before[k] / load_before[k]: thời điểm khởi hành & tải trọng của xe NGAY
             TRƯỚC khi đi tới stops[k] trên route GỐC (route gốc vốn đã hợp lệ, không đổi
             suốt vòng lặp này). Nhờ vậy, khi thử chèn ở vị trí i, không cần mô phỏng lại
             từ Depot -> đọc thẳng dep_before[i]/load_before[i] là có ngay trạng thái đúng.
          3. Với j: quét i -> n MỘT LƯỢT DUY NHẤT (không quay lại từ đầu cho mỗi j), vừa
             đi vừa cập nhật trạng thái "xe đang mang bưu kiện mới, chưa giao" -> mỗi bước
             advance chỉ O(1), nên tổng công cho tất cả j (với 1 i cố định) là O(n) thay vì
             O(n^2) -> hạ độ phức tạp từ O(n^3) xuống O(n^2) cho khâu TÌM ứng viên.
          4. Các kiểm tra pickup/dropoff CỤC BỘ dùng ĐÚNG công thức trong utils.py
             (calculate_next_time, calculate_next_load - cùng hàm mà utils.py định nghĩa,
             không phải công thức viết lại/xấp xỉ) -> nếu 1 ứng viên bị loại ở bước này,
             chắc chắn is_route_valid() cũng sẽ loại nó -> loại sớm an toàn, không làm mất
             ứng viên hợp lệ nào.
          5. Phần DUY NHẤT các bước 2-4 KHÔNG kiểm tra được là ảnh hưởng lên phần ĐUÔI route
             (sau vị trí dropoff j) - vì chèn thêm có thể làm các điểm dừng PHÍA SAU bị trễ
             giờ dây chuyền. Nên với ứng viên "có vẻ ổn" sau bước 2-4, vẫn dựng route đầy đủ
             và gọi is_route_valid() 1 lần để xác nhận - ĐÚNG NHƯ BẢN GỐC, không bỏ qua.
        """
        best_req, best_taxi_idx, best_i, best_j, max_gain = None, None, None, None, 0.0
        cost_mat = self.instance.cost_matrix
        time_mat = self.instance.time_matrix
        get_windows = self.instance.get_node_time_windows
        get_parcel = self.instance.get_parcel_by_node

        def node_weight(node: Node) -> float:
            if node.type in ('PARCEL_PICKUP', 'PARCEL_DROPOFF'):
                parcel = get_parcel(node)
                return parcel.weight if parcel else 0.0
            return 0.0

        # ---- Bước 1: tính trước dep_before / load_before / forbidden_gap cho TẤT CẢ xe,
        #      CHỈ 1 LẦN duy nhất (không phải 1 lần / mỗi request như hàm ban đầu tính ngầm
        #      bằng cách gọi is_route_valid từ đầu mỗi lần). Vẫn giữ đúng thứ tự lặp GỐC
        #      (request ngoài, xe trong) ở bước 2 để trường hợp HÒA gain (2 phương án cùng
        #      lợi nhuận tuyệt đối) được chọn giống 100% bản gốc, không lệch do đổi thứ tự.
        taxi_caches = []
        for t_idx, route in enumerate(self.routes):
            stops = route.stops
            n = len(stops)
            depot = route.taxi.depot_node
            capacity = route.taxi.capacity

            dep_before = [0.0] * (n + 1)
            load_before = [0.0] * (n + 1)
            forbidden_gap = [False] * (n + 1)  # True = "khe hở" này đang nằm giữa 1 cặp đón/trả khách

            cur_time, cur_load, cur_node = 0.0, 0.0, depot
            for k in range(n):
                dep_before[k] = cur_time
                load_before[k] = cur_load
                if k > 0 and stops[k - 1].type == 'PASSENGER_PICKUP':
                    forbidden_gap[k] = True

                node = stops[k]
                early_v, late_v, service_v = get_windows(node)
                # route gốc luôn hợp lệ (đã qua is_route_valid trước đó khi được chèn vào),
                # nên bước mô phỏng lại này không thể trả về None ở đây trong thực tế.
                time_res = calculate_next_time(cur_time, cur_node.matrix_index, node.matrix_index,
                                                time_mat, early_v, late_v, service_v)
                cur_time = time_res[2] if time_res is not None else float('inf')
                new_load = calculate_next_load(cur_load, node.type, node_weight(node), capacity)
                cur_load = new_load if new_load is not None else cur_load
                cur_node = node
            dep_before[n] = cur_time
            load_before[n] = cur_load
            if n > 0 and stops[n - 1].type == 'PASSENGER_PICKUP':
                forbidden_gap[n] = True

            taxi_caches.append((route, n, depot, capacity, dep_before, load_before, forbidden_gap))

        # ---- Bước 2: quét request (ngoài) x xe (trong) - ĐÚNG thứ tự bản gốc ----
        for req in self.unserved_parcels:
            p_node, d_node = req.pickup_node, req.dropoff_node
            early_p, late_p, service_p = get_windows(p_node)
            early_d, late_d, service_d = get_windows(d_node)

            for t_idx, (route, n, depot, capacity, dep_before, load_before, forbidden_gap) in enumerate(taxi_caches):
                stops = route.stops

                for i in range(n + 1):
                    if forbidden_gap[i]:
                        continue

                    prev_node = depot if i == 0 else stops[i - 1]
                    u, v = prev_node.matrix_index, p_node.matrix_index
                    if math.isinf(cost_mat[u][v]) or math.isinf(time_mat[u][v]):
                        continue

                    # --- Kiểm tra chèn pickup tại i: ĐÚNG công thức is_route_valid sẽ dùng,
                    #     không phải ước lượng -> loại ở đây là loại đúng, an toàn ---
                    time_res = calculate_next_time(dep_before[i], u, v, time_mat, early_p, late_p, service_p)
                    if time_res is None:
                        continue
                    dep_p = time_res[2]

                    load_after_p = calculate_next_load(load_before[i], 'PARCEL_PICKUP', req.weight, capacity)
                    if load_after_p is None:
                        continue

                    # --- Quét j từ i -> n trong 1 LƯỢT DUY NHẤT (không quay lại từ đầu) ---
                    running_time, running_load, running_prev = dep_p, load_after_p, p_node

                    for j in range(i, n + 1):
                        if not forbidden_gap[j]:
                            u2, v2 = running_prev.matrix_index, d_node.matrix_index
                            if not (math.isinf(cost_mat[u2][v2]) or math.isinf(time_mat[u2][v2])):
                                drop_res = calculate_next_time(running_time, u2, v2, time_mat,
                                                                early_d, late_d, service_d)
                                if drop_res is not None:
                                    # Qua được kiểm tra cục bộ (đón, mang, giao) -> vẫn còn phải
                                    # xác nhận phần ĐUÔI route (sau j) bằng is_route_valid() thật,
                                    # ĐÚNG NHƯ BẢN GỐC - không bỏ qua bước này.
                                    temp_stops = stops[:i] + [p_node] + stops[i:j] + [d_node] + stops[j:]
                                    temp_route = Route(taxi=route.taxi, stops=temp_stops)
                                    if is_route_valid(temp_route, self.instance):
                                        delta_cost = self.get_parcel_delta_cost(route, p_node, d_node, i, j)
                                        gain = req.revenue - delta_cost
                                        if gain > max_gain:
                                            max_gain = gain
                                            best_req, best_taxi_idx, best_i, best_j = req, t_idx, i, j

                        if j >= n:
                            break

                        # Đi tiếp qua stops[j] (bưu kiện mới VẪN ở trên xe, chưa giao) để
                        # chuẩn bị xét j+1 - chỉ tốn O(1), không quay lại từ đầu.
                        node_j = stops[j]
                        u3, v3 = running_prev.matrix_index, node_j.matrix_index
                        if math.isinf(cost_mat[u3][v3]) or math.isinf(time_mat[u3][v3]):
                            break  # đứt đường -> mọi j lớn hơn cũng vô nghĩa, dừng sớm

                        early_j, late_j, service_j = get_windows(node_j)
                        adv_res = calculate_next_time(running_time, u3, v3, time_mat, early_j, late_j, service_j)
                        if adv_res is None:
                            break  # đến muộn dù chưa kịp giao D -> mọi j lớn hơn cũng vô nghĩa

                        new_running_load = calculate_next_load(running_load, node_j.type, node_weight(node_j), capacity)
                        if new_running_load is None:
                            break  # vượt tải dù chưa kịp giao D -> mọi j lớn hơn cũng vô nghĩa

                        running_time = adv_res[2]
                        running_load = new_running_load
                        running_prev = node_j

        return best_req, best_taxi_idx, best_i, best_j, max_gain

    def solve(self) -> List[Route]:
        """Vòng lặp Greedy chèn đơn cho đến khi không còn đơn nào (khách hoặc bưu kiện) giúp tăng Benefit."""
        while True:
            # 1. Tìm phương án chèn tốt nhất cho Hành khách và Bưu kiện, ĐỘC LẬP với nhau
            pass_req, p_taxi, p_pos, p_gain = self.find_best_passenger_insertion()
            parcel_req, r_taxi, r_i, r_j, r_gain = self.find_best_parcel_insertion()

            # 2. So sánh 2 phương án, thực hiện chèn phương án có Gain lớn nhất (miễn > 0)
            if p_gain > 0 and p_gain >= r_gain:
                # Chọn phương án chèn khách vì gain của nó lớn hơn (hoặc bằng) gain của hàng
                nodes = [pass_req.pickup_node, pass_req.dropoff_node]
                self.routes[p_taxi].stops = (
                    self.routes[p_taxi].stops[:p_pos] + nodes + self.routes[p_taxi].stops[p_pos:]
                )
                self.unserved_passengers.remove(pass_req)  # Đánh dấu đã phục vụ, không xét lại nữa

            elif r_gain > 0 and r_gain > p_gain:
                # Chọn phương án chèn hàng vì gain của nó lớn hơn
                p_node, d_node = parcel_req.pickup_node, parcel_req.dropoff_node
                self.routes[r_taxi].stops = (
                    self.routes[r_taxi].stops[:r_i] + [p_node] + self.routes[r_taxi].stops[r_i:r_j] + [d_node] + self.routes[r_taxi].stops[r_j:]
                )
                self.unserved_parcels.remove(parcel_req)

            else:
                # Ngắt vòng lặp khi không còn chèn thêm được đơn nào có lợi nhuận dương
                # (cả p_gain và r_gain đều <= 0, hoặc không tìm được request nào để chèn)
                break

        return self.routes


def insert_passenger_request_direct(
    route: Route,
    passenger_req: PassengerRequest,
    insert_idx: int
) -> Optional[List[Node]]:
    """
    Tạo danh sách stops mới khi chèn một Yêu cầu Hành khách vào vị trí insert_idx.
    Đảm bảo cấu trúc cặp kề nhau [P_i^n, D_i^n] để không bao giờ vi phạm Công thức (7).

    Hàm này hiện KHÔNG được gọi ở đâu trong solve() (GreedySolver tự nối list trực tiếp),
    có thể được viết ra để dùng riêng lẻ khi cần chèn thủ công / test, hoặc dự phòng cho
    một phiên bản thuật toán khác (ví dụ ALNS) sau này.
    """
    current_stops = route.stops

    new_stops = (
        current_stops[:insert_idx] +
        [passenger_req.pickup_node, passenger_req.dropoff_node] +
        current_stops[insert_idx:]
    )

    return new_stops


def calculate_objective_value(routes: List[Route], instance: ProblemInstance) -> float:
    """Tính tổng Benefit = Tổng Doanh thu đơn đã phục vụ - Tổng Chi phí di chuyển của các xe."""
    total_revenue = 0.0
    total_cost = 0.0

    for route in routes:
        if not route.stops:
            continue  # Xe không chạy chuyến nào thì không tốn chi phí, cũng không có doanh thu

        # 1. Chi phí di chuyển của xe k: cộng dồn từ Depot qua từng điểm dừng
        cost_mat = instance.cost_matrix
        c_route = cost_mat[route.taxi.depot_node.matrix_index][route.stops[0].matrix_index]
        for idx in range(len(route.stops) - 1):
            c_route += cost_mat[route.stops[idx].matrix_index][route.stops[idx + 1].matrix_index]
        total_cost += c_route

        # 2. Doanh thu từ các đơn được phục vụ: chỉ cộng doanh thu tại điểm PICKUP
        #    (để không bị cộng trùng 2 lần cho cùng 1 đơn, vì mỗi đơn có cả pickup và dropoff)
        for node in route.stops:
            if node.type == 'PASSENGER_PICKUP':
                p = instance.get_passenger_by_node(node)
                if p:
                    total_revenue += p.revenue
            elif node.type == 'PARCEL_PICKUP':
                h = instance.get_parcel_by_node(node)
                if h:
                    total_revenue += h.revenue

    return total_revenue - total_cost


# ======================================================================
# random_solver.py
# ======================================================================

# Cài đặt thuật toán RANDOM INSERTION: khác với Greedy (luôn chọn phương án
# lời nhất), Random chỉ xáo trộn thứ tự đơn/vị trí rồi chèn phương án khả thi đầu tiên
# tìm thấy (miễn hợp lệ và có lời > 0), không so sánh để tìm phương án tốt nhất.
# Dùng để: (1) làm baseline so sánh chất lượng với Greedy, (2) làm phương án dự phòng khi Greedy chạy quá lâu.


class RandomSolver:
    """
    Thuật toán Random Insertion (Phương án dự phòng).
    Xáo trộn ngẫu nhiên thứ tự đơn và vị trí chèn, tự động bỏ qua các phương án vi phạm ràng buộc.
    """
    def __init__(self, instance: ProblemInstance, max_attempts: int = 50, seed: Optional[int] = None):
        self.instance = instance
        self.max_attempts = max_attempts  # Khai báo nhưng hiện KHÔNG được dùng ở đâu trong solve()
        if seed is not None:
            random.seed(seed)             # Cố định seed để kết quả random lặp lại được khi cần debug/so sánh

    def _get_route_cost(self, route: Route) -> float:
        """Tính tổng chi phí di chuyển của 1 lộ trình từ đầu (giống hệt logic trong GreedySolver)."""
        stops = route.stops
        if not stops:
            return 0.0
        cost_mat = self.instance.cost_matrix
        cost = cost_mat[route.taxi.depot_node.matrix_index][stops[0].matrix_index]
        for idx in range(len(stops) - 1):
            cost += cost_mat[stops[idx].matrix_index][stops[idx + 1].matrix_index]
        return cost

    def _calculate_delta_cost(self, route: Route, new_stops: List[Node]) -> float:
        """
        Tính delta cost bằng cách tính lại toàn bộ chi phí (route cũ và route mới) rồi trừ nhau.
        Khác với GreedySolver (tính delta O(1) bằng công thức cạnh), ở đây tính O(n) mỗi lần
        vì RandomSolver không cần tối ưu tốc độ bằng Greedy (không phải tìm phương án TỐT NHẤT
        trong tất cả tổ hợp, chỉ cần tìm 1 phương án khả thi bất kỳ).
        """
        old_cost = self._get_route_cost(route)
        temp_route = Route(taxi=route.taxi, stops=new_stops)
        return self._get_route_cost(temp_route) - old_cost

    def solve(self) -> List[Route]:
        routes = [Route(taxi=t) for t in self.instance.taxis]
        unserved_passengers = list(self.instance.passengers)
        unserved_parcels = list(self.instance.parcels)

        # Xáo trộn danh sách đơn hàng -> mỗi lần chạy (seed khác) sẽ ưu tiên phục vụ đơn theo thứ tự khác nhau
        random.shuffle(unserved_passengers)
        random.shuffle(unserved_parcels)

        # 1. Chèn ngẫu nhiên Hành khách
        for req in unserved_passengers[:]:  # Dùng [:] để lặp trên bản sao, an toàn nếu sau này có remove
            nodes = [req.pickup_node, req.dropoff_node]
            taxi_indices = list(range(len(routes)))
            random.shuffle(taxi_indices)  # Xáo trộn thứ tự thử các xe

            inserted = False
            for t_idx in taxi_indices:
                route = routes[t_idx]
                n_stops = len(route.stops)
                positions = list(range(n_stops + 1))
                random.shuffle(positions)  # Xáo trộn thứ tự thử các vị trí chèn trên xe này

                for pos in positions:
                    temp_stops = route.stops[:pos] + nodes + route.stops[pos:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    # Bỏ qua nếu vi phạm ràng buộc cứng (4 loại bảo toàn luồng)
                    if not is_route_valid(temp_route, self.instance):
                        continue

                    # Bỏ qua nếu lợi nhuận không dương (chèn vào bị lỗ thì không đáng)
                    delta_cost = self._calculate_delta_cost(route, temp_stops)
                    if req.revenue - delta_cost <= 0:
                        continue

                    # Thỏa mãn cả 2 điều kiện -> chèn ngay lập tức (không tìm vị trí tốt hơn nữa)
                    routes[t_idx].stops = temp_stops
                    inserted = True
                    break  # Thoát vòng lặp vị trí

                if inserted:
                    break  # Thoát vòng lặp xe, không thử xe khác nữa vì đã chèn thành công

        # 2. Chèn ngẫu nhiên Bưu kiện (logic tương tự, nhưng thử cả cặp vị trí (i, j))
        for req in unserved_parcels[:]:
            p_node, d_node = req.pickup_node, req.dropoff_node
            taxi_indices = list(range(len(routes)))
            random.shuffle(taxi_indices)

            inserted = False
            for t_idx in taxi_indices:
                route = routes[t_idx]
                n_stops = len(route.stops)

                # Tạo danh sách tất cả cặp (i, j) hợp lệ với i <= j (lấy hàng trước hoặc cùng lúc giao)
                candidate_pairs = [(i, j) for i in range(n_stops + 1) for j in range(i, n_stops + 1)]
                random.shuffle(candidate_pairs)  # Xáo trộn để thử theo thứ tự ngẫu nhiên

                for i, j in candidate_pairs:
                    temp_stops = route.stops[:i] + [p_node] + route.stops[i:j] + [d_node] + route.stops[j:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    if not is_route_valid(temp_route, self.instance):
                        continue

                    delta_cost = self._calculate_delta_cost(route, temp_stops)
                    if req.revenue - delta_cost <= 0:
                        continue

                    routes[t_idx].stops = temp_stops
                    inserted = True
                    break

                if inserted:
                    break

        return routes


# ======================================================================
# operators.py
# ======================================================================

# Làm nhiệm vụ biến đổi cấu trúc danh sách stops (List[Node]),
# Mỗi hàm ở đây nhận vào (các) route hiện tại, trả về route mới (không sửa route cũ
# tại chỗ) để dễ so sánh trước/sau khi tính delta cost/benefit.
#
# "Pair Mode": theo Công thức (7) trong đề bài, một khách hàng luôn phải đi liền cặp
# [Pickup, Dropoff] — không được tách rời trong bất kỳ route nào. Vì vậy mọi thao tác
# di chuyển/hoán đổi một node hành khách đều phải kéo theo node còn lại của cặp đó.
# Bưu kiện thì không bị ràng buộc này nên chỉ di chuyển đúng 1 node.
#
# Phân loại toán tử:
#   - relocate(): toán tử nội 1 xe (intra_route) — di chuyển 1 request trong CÙNG 1 route.
#   - swap():     toán tử giữa các xe (inter_route) — hoán đổi request giữa route1 và route2.
#                 (route1 và route2 có thể là cùng 1 route, khi đó swap() hoạt động
#                  như 1 toán tử intra_route hoán đổi 2 request trong cùng 1 xe.)

def _get_request_block(
    route: List[Node],
    idx: int,
    instance: ProblemInstance
) -> Optional[Tuple[int, int, List[Node]]]:
    """
    Hàm nội bộ (không export): xác định "khối" (block) node cần di chuyển cùng nhau
    khi thao tác lên vị trí idx trong route.

    - Nếu route[idx] là PASSENGER_PICKUP hoặc PASSENGER_DROPOFF: trả về block gồm
      CẢ 2 node liền kề [Pickup, Dropoff] của khách đó (đúng Pair Mode).
    - Nếu route[idx] là bưu kiện (hoặc loại khác): trả về block chỉ gồm chính node đó.

    Trả về (lo, hi, block_nodes):
        lo, hi   : chỉ số đầu/cuối của block trong route gốc (lo <= hi)
        block_nodes: danh sách node theo đúng thứ tự [Pickup, Dropoff] (nếu là khách)

    Trả về None nếu index không hợp lệ, hoặc route không đúng bất biến Công thức (7)
    (ví dụ Pickup/Dropoff của cùng 1 khách không nằm liền kề nhau) — trường hợp này
    coi là lỗi dữ liệu đầu vào, không cố xử lý để tránh làm hỏng route âm thầm.
    """
    if not (0 <= idx < len(route)):
        return None

    node = route[idx]

    if node.type == 'PASSENGER_PICKUP':
        req = instance.get_passenger_by_node(node)
        if req is None:
            return None
        # Theo Công thức (7), Dropoff phải nằm ngay sau Pickup
        if idx + 1 >= len(route) or route[idx + 1].id != req.dropoff_node.id:
            return None
        return idx, idx + 1, [route[idx], route[idx + 1]]

    elif node.type == 'PASSENGER_DROPOFF':
        req = instance.get_passenger_by_node(node)
        if req is None:
            return None
        # Pickup phải nằm ngay trước Dropoff
        if idx - 1 < 0 or route[idx - 1].id != req.pickup_node.id:
            return None
        return idx - 1, idx, [route[idx - 1], route[idx]]

    else:
        # Bưu kiện (hoặc node đơn lẻ khác): không có ràng buộc đi cặp, block = chính nó
        return idx, idx, [node]


def relocate(
    route: List[Node],
    node_idx: int,
    target_idx: int,
    instance: ProblemInstance
) -> Optional[List[Node]]:
    """
    [Toán tử intra_route] Di chuyển 1 request (bưu kiện: 1 node; hành khách: cả cặp
    [Pickup, Dropoff]) từ vị trí node_idx sang vị trí target_idx, trong cùng 1 route.

    Tham số:
        route:      danh sách stops hiện tại của 1 xe (không bị chỉnh sửa tại chỗ)
        node_idx:   vị trí (trong route) của node muốn di chuyển — có thể trỏ vào
                    Pickup hoặc Dropoff của 1 khách, hàm sẽ tự nhận diện và kéo theo
                    node còn lại (Pair Mode)
        target_idx: vị trí muốn chèn block vào, được tính trên route sau khi đã bỏ
                    block cũ ra (tức là index trong danh sách "phần còn lại")
        instance:   dùng để tra request tương ứng với node (get_passenger_by_node)

    Trả về route mới (list Node), hoặc None nếu thao tác không hợp lệ về cấu trúc
    (index sai, hoặc route đầu vào không đúng bất biến Công thức 7).

    Lưu ý: hàm này không kiểm tra ràng buộc thời gian/tải trọng — việc đó do
    evaluator.py / validator.py đảm nhiệm sau khi có route mới.
    """
    block = _get_request_block(route, node_idx, instance)
    if block is None:
        return None
    lo, hi, block_nodes = block

    # Route sau khi loại bỏ block cũ (không đụng route gốc, tạo list mới)
    remaining = route[:lo] + route[hi + 1:]

    if not (0 <= target_idx <= len(remaining)):
        return None

    # Chèn nguyên block vào vị trí target_idx trong phần còn lại
    return remaining[:target_idx] + block_nodes + remaining[target_idx:]


def swap(
    route1: List[Node],
    route2: List[Node],
    node_idx1: int,
    node_idx2: int,
    instance: ProblemInstance
) -> Optional[Tuple[List[Node], List[Node]]]:
    """
    [Toán tử inter_route, dùng được cho cả intra_route khi route1 is route2]
    Hoán đổi request tại vị trí node_idx1 (trong route1) với request tại vị trí
    node_idx2 (trong route2). Nếu 1 trong 2 (hoặc cả 2) là hành khách, hoán đổi
    NGUYÊN CẶP [Pickup, Dropoff] của khách đó (Pair Mode) — không tách lẻ.

    - Nếu route1 và route2 là 2 route khác nhau: đây là toán tử inter_route
      (đổi request giữa 2 xe khác nhau).
    - Nếu route1 is route2 (cùng 1 route): hàm hoạt động như toán tử intra_route,
      hoán đổi vị trí 2 request trong CÙNG 1 xe.

    Trả về (route1_mới, route2_mới), hoặc None nếu thao tác không hợp lệ (index sai,
    route không đúng bất biến, hoặc 2 block được chọn bị chồng lấn khi route1 is route2).
    """
    block1 = _get_request_block(route1, node_idx1, instance)
    block2 = _get_request_block(route2, node_idx2, instance)
    if block1 is None or block2 is None:
        return None

    lo1, hi1, nodes1 = block1
    lo2, hi2, nodes2 = block2

    if route1 is route2:
        # --- Trường hợp intra_route: swap 2 block trong CÙNG 1 danh sách ---
        # Kiểm tra 2 block có dùng chung ít nhất 1 vị trí không (không hợp lệ nếu có)
        if lo1 <= hi2 and lo2 <= hi1:
            return None

        route = route1
        # Sắp lại để block "a" luôn đứng trước block "b" theo chỉ số, cho dễ ghép nối
        if lo1 <= lo2:
            a_lo, a_hi, a_nodes = lo1, hi1, nodes1
            b_lo, b_hi, b_nodes = lo2, hi2, nodes2
        else:
            a_lo, a_hi, a_nodes = lo2, hi2, nodes2
            b_lo, b_hi, b_nodes = lo1, hi1, nodes1

        new_route = (
            route[:a_lo] + b_nodes +           # chỗ của block a giờ chứa nội dung block b
            route[a_hi + 1:b_lo] +             # phần ở giữa 2 block giữ nguyên
            a_nodes +                          # chỗ của block b giờ chứa nội dung block a
            route[b_hi + 1:]
        )
        return new_route, new_route

    else:
        # --- Trường hợp inter_route: 2 route độc lập, không cần lo chồng lấn chỉ số ---
        #
        # chặn 1 trường hợp quan trọng: _get_request_block() trả về block chỉ gồm 1 node
        # cho bưu kiện (vì bưu kiện được phép tách rời pickup/dropoff trong cùng 1 route,
        # nên khác với khách không cần bắt cặp liền kề). Nhưng nếu ta di chuyển đúng 1 node
        # đó (ví dụ chỉ mỗi điểm lấy hàng) sang một xe khác, điểm giao hàng còn lại của
        # đúng bưu kiện đó vẫn nằm ở route cũ -> bưu kiện bị "xẻ đôi" cho 2 xe khác nhau,
        # điều không thể xảy ra trong thực tế (1 xe vật lý mới chở được từ lúc lấy đến lúc giao).
        # Vì vậy: chỉ cho phép swap() giữa 2 route khác nhau khi cả 2 block đều là
        # cặp hành khách (đủ 2 node, đã tự bảo toàn Pair Mode) — từ chối (trả None) nếu
        # có block nào là 1 node bưu kiện đơn lẻ.
        for nodes in (nodes1, nodes2):
            if len(nodes) == 1 and nodes[0].type in ('PARCEL_PICKUP', 'PARCEL_DROPOFF'):
                return None

        new_route1 = route1[:lo1] + nodes2 + route1[hi1 + 1:]
        new_route2 = route2[:lo2] + nodes1 + route2[hi2 + 1:]
        return new_route1, new_route2


# Test
# Khối test dưới đây tự dựng 1 ProblemInstance nhỏ, áp dụng relocate()/swap(),
# rồi dùng is_route_valid() (file validator.py có sẵn, không sửa) để xác nhận
# route sinh ra vẫn giữ đúng cấu trúc bất biến (đặc biệt là Pair Mode).

def _test_operators():

    # --- Dựng dữ liệu tối thiểu: đủ node để test relocate/swap, không cần ma trận thật ---
    depot = Node(id=0, type='DEPOT', matrix_index=0)

    pa_p, pa_d = Node(id=1, type='PASSENGER_PICKUP', matrix_index=1), Node(id=2, type='PASSENGER_DROPOFF', matrix_index=2)
    pb_p, pb_d = Node(id=3, type='PASSENGER_PICKUP', matrix_index=3), Node(id=4, type='PASSENGER_DROPOFF', matrix_index=4)
    hc_p, hc_d = Node(id=5, type='PARCEL_PICKUP', matrix_index=5), Node(id=6, type='PARCEL_DROPOFF', matrix_index=6)

    passengers = [
        PassengerRequest(id=1, pickup_node=pa_p, dropoff_node=pa_d, revenue=100.0,
                          early_pickup=0.0, late_pickup=100.0, service_time=1.0),
        PassengerRequest(id=2, pickup_node=pb_p, dropoff_node=pb_d, revenue=80.0,
                          early_pickup=0.0, late_pickup=100.0, service_time=1.0),
    ]
    parcels = [
        ParcelRequest(id=1, pickup_node=hc_p, dropoff_node=hc_d, revenue=60.0, weight=3.0,
                       early_pickup=0.0, late_pickup=100.0, early_dropoff=0.0, late_dropoff=100.0,
                       service_time=1.0),
    ]
    taxi1 = Taxi(id=1, depot_node=depot, capacity=10.0)
    taxi2 = Taxi(id=2, depot_node=depot, capacity=10.0)

    # Ma trận giả (không dùng trong test này, chỉ cần tồn tại để ProblemInstance khởi tạo được)
    n_nodes = 7
    fake_matrix = [[0.0] * n_nodes for _ in range(n_nodes)]

    instance = ProblemInstance(
        taxis=[taxi1, taxi2], passengers=passengers, parcels=parcels,
        time_matrix=fake_matrix, cost_matrix=fake_matrix
    )

    print("=" * 60)
    print("TEST 1: relocate() — di chuyển khách A ra cuối route")
    print("=" * 60)
    route1 = [pa_p, pa_d, hc_p, hc_d]
    print(f"Route trước: {[n.id for n in route1]}")
    new_route1 = relocate(route1, node_idx=0, target_idx=2, instance=instance)  # trỏ vào Pickup của khách A
    print(f"Route sau:   {[n.id for n in new_route1]}")
    check_route = Route(taxi=taxi1, stops=new_route1)
    print(f"Vẫn đúng Pair Mode (Công thức 7)? {validate_direct_passenger_flow(check_route, instance)}")
    print(f"Route gốc route1 có bị đổi không (phải KHÔNG đổi)? {[n.id for n in route1] == [1, 2, 5, 6]}")

    print("\n" + "=" * 60)
    print("TEST 2: relocate() trỏ vào Dropoff — vẫn phải kéo theo cả cặp")
    print("=" * 60)
    route2 = [hc_p, hc_d, pa_p, pa_d]
    print(f"Route trước: {[n.id for n in route2]}")
    new_route2 = relocate(route2, node_idx=3, target_idx=0, instance=instance)  # trỏ vào Dropoff (id=2) của khách A
    print(f"Route sau:   {[n.id for n in new_route2]}")
    check_route2 = Route(taxi=taxi1, stops=new_route2)
    print(f"Vẫn đúng Pair Mode? {validate_direct_passenger_flow(check_route2, instance)}")

    print("\n" + "=" * 60)
    print("TEST 3a: swap() giữa 2 route khác nhau (inter_route) — đổi khách A với khách B")
    print("=" * 60)
    route_x = [pa_p, pa_d]
    route_y = [pb_p, pb_d]
    print(f"route_x trước: {[n.id for n in route_x]}, route_y trước: {[n.id for n in route_y]}")
    new_x, new_y = swap(route_x, route_y, node_idx1=0, node_idx2=1, instance=instance)  # trỏ vào Dropoff của B cũng được
    print(f"route_x sau:   {[n.id for n in new_x]}, route_y sau:   {[n.id for n in new_y]}")
    print(f"Pair Mode ở route_x mới? {validate_direct_passenger_flow(Route(taxi=taxi1, stops=new_x), instance)}")
    print(f"Pair Mode ở route_y mới? {validate_direct_passenger_flow(Route(taxi=taxi2, stops=new_y), instance)}")

    print("\n" + "=" * 60)
    print("TEST 3b: swap() giữa 2 route khác nhau với 1 node bưu kiện đơn lẻ -> phải bị TỪ CHỐI")
    print("=" * 60)
    route_p = [pa_p, pa_d]
    route_q = [hc_p, hc_d]
    print(f"route_p: {[n.id for n in route_p]}, route_q: {[n.id for n in route_q]}")
    result_reject = swap(route_p, route_q, node_idx1=0, node_idx2=0, instance=instance)  # node_idx2=0 -> chỉ mỗi hc_p
    print(f"Kết quả (kỳ vọng None, vì sẽ xẻ đôi bưu kiện C cho 2 xe): {result_reject}")

    print("\n" + "=" * 60)
    print("TEST 4: swap() trong CÙNG 1 route (intra_route) — đổi khách A với khách B")
    print("=" * 60)
    route_z = [pa_p, pa_d, hc_p, hc_d, pb_p, pb_d]
    print(f"Route trước: {[n.id for n in route_z]}")
    new_z1, new_z2 = swap(route_z, route_z, node_idx1=0, node_idx2=4, instance=instance)
    print(f"Route sau:   {[n.id for n in new_z1]}")
    print(f"Pair Mode? {validate_direct_passenger_flow(Route(taxi=taxi1, stops=new_z1), instance)}")

    print("\n" + "=" * 60)
    print("TEST 5: swap() với 2 block chồng lấn -> phải trả về None")
    print("=" * 60)
    result = swap(route_z, route_z, node_idx1=0, node_idx2=1, instance=instance)  # cùng 1 khách A
    print(f"Kết quả (kỳ vọng None): {result}")


# ======================================================================
# hill_climbing.py
# ======================================================================

# TODO: Sau này sẽ import operators từ nhánh của Hà Thu
# from operators import relocate, swap


class HillClimbingSolver:
    def __init__(self, instance: ProblemInstance, initial_routes: List[List[Node]]):

        self.instance = instance

        self.routes = copy.deepcopy(initial_routes)

        self.MAX_NON_IMPROVING_STEPS = 500

    def solve(self) -> List[List[Node]]:
        """
        Vòng lặp chính của Hill Climbing.
        """
        non_improving_steps = 0
        iteration = 0

        print("Bắt đầu chạy Hill Climbing...")

        
        while non_improving_steps < self.MAX_NON_IMPROVING_STEPS:
            iteration += 1

            mock_result = self._mock_relocate_operator()
            if not mock_result:
                non_improving_steps += 1
                continue
                
            route_idx, insert_idx, node_A, node_B, insert_node = mock_result

            delta_cost = calculate_delta_cost(node_A, node_B, insert_node, self.instance.cost_matrix)
            
            delta_benefit = -delta_cost 

          
            if delta_benefit <= 0:
                non_improving_steps += 1
                continue

            # Lấy đúng capacity của XE đang được xét (route_idx), không phải xe số 0 cố định.
            # Trước đây dùng self.instance.vehicles[0].capacity -> sai vì ProblemInstance
            # không có field "vehicles" (chỉ có "taxis"), nên sẽ crash ngay khi delta_benefit > 0.
            capacity = self.instance.taxis[route_idx].capacity

            # Node không tự lưu "weight" (weight chỉ nằm trong ParcelRequest), nên phải tra cứu
            # qua instance bằng get_parcel_by_node(). Trước đây insert_node.weight sẽ crash với
            # AttributeError ngay khi gặp 1 node bưu kiện thật (từ operators.py của Hà Thu).
            if insert_node.type == 'PARCEL_PICKUP':
                parcel = self.instance.get_parcel_by_node(insert_node)
                weight = parcel.weight if parcel else 0.0
            else:
                weight = 0.0

            mock_current_loads = [0.0] * len(self.routes[route_idx])
            is_capacity_valid = check_capacity_delta(
                route_stops=self.routes[route_idx],
                insert_idx=insert_idx,
                insert_node=insert_node,
                capacity=capacity,
                current_loads=mock_current_loads,
                weight=weight
            )

            if not is_capacity_valid:
                non_improving_steps += 1
                continue

            delta_time = calculate_delta_time(
                dep_A=0.0, 
                node_A=node_A,
                node_B=node_B,
                old_dep_B=10.0,
                insert_node=insert_node,
                instance=self.instance
            )
            
            if delta_time is None: # Tức là bị vi phạm (đến muộn)
                non_improving_steps += 1
                continue

            print(f"[Iter {iteration}] Tìm thấy nghiệm tốt hơn! Tiết kiệm: {delta_benefit:.2f}")
            
    
            self.routes[route_idx].insert(insert_idx, insert_node)
   
            non_improving_steps = 0 

        print(f"Thuật toán dừng lại sau {iteration} vòng lặp.")
        return self.routes

    def _mock_relocate_operator(self) -> Optional[Tuple[int, int, Node, Node, Node]]:
        if not self.routes:
            return None
            
        route_idx = random.randint(0, len(self.routes) - 1)
        route = self.routes[route_idx]
        
        if len(route) < 2:
            return None


        insert_idx = random.randint(1, len(route) - 1)
        node_A = route[insert_idx - 1]
        node_B = route[insert_idx]
        
        insert_node = Node(id="MOCK", matrix_index=0, type="PASSENGER_PICKUP")
        
        return (route_idx, insert_idx, node_A, node_B, insert_node)


# ======================================================================
# main.py (demo / benchmark)
# ======================================================================

# 1: Sinh dữ liệu mẫu nhỏ

def generate_demo_instance() -> ProblemInstance:
    """
    Sinh 1 test case NHỎ (2 hành khách, 2 bưu kiện, 2 xe) với tọa độ
    tường minh, để có thể tự tính tay và so sánh với kết quả của code
    Quy ước: cost = khoảng cách Euclid, time = cost / 2.0 )
    """

    # (id_node, type, (x, y))
    coords = [
        (0, 'DEPOT',             (0, 0)),
        (1, 'PASSENGER_PICKUP',  (2, 0)),   # Khách A đón
        (2, 'PASSENGER_DROPOFF', (2, 3)),   # Khách A trả
        (3, 'PASSENGER_PICKUP',  (4, 0)),   # Khách B đón
        (4, 'PASSENGER_DROPOFF', (4, 2)),   # Khách B trả
        (5, 'PARCEL_PICKUP',     (1, 1)),   # Hàng C lấy
        (6, 'PARCEL_DROPOFF',    (5, 1)),   # Hàng C giao
        (7, 'PARCEL_PICKUP',     (3, 3)),   # Hàng D lấy
        (8, 'PARCEL_DROPOFF',    (0, 4)),   # Hàng D giao
    ]

    # Tạo danh sách đối tượng Node từ coords (mỗi Node ứng với 1 dòng trong ma trận)
    nodes = [Node(id=i, type=t, matrix_index=i) for i, t, _ in coords]

    # Tách riêng phần tọa độ (x, y) ra để tính khoảng cách
    xy = [c for _, _, c in coords]

    n = len(nodes)

    # Khởi tạo ma trận chi phí và ma trận thời gian toàn số 0, kích thước n x n
    cost_matrix = [[0.0] * n for _ in range(n)]
    time_matrix = [[0.0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if r != c:  # Không tính khoảng cách từ 1 node đến chính nó (giữ = 0)
                dx = xy[r][0] - xy[c][0]
                dy = xy[r][1] - xy[c][1]

                # Khoảng cách Euclid giữa 2 điểm, làm tròn 2 chữ số thập phân
                dist = round(math.hypot(dx, dy), 2)
                cost_matrix[r][c] = dist                  # Chi phí = khoảng cách
                time_matrix[r][c] = round(dist / 2.0, 2)  # Thời gian = chi phí / tốc độ (2 đơn vị/thời gian)
 
    # Khai báo 2 yêu cầu Hành khách, mỗi yêu cầu gắn với 1 cặp node (pickup, dropoff)
    passengers = [
        PassengerRequest(
            id=1, pickup_node=nodes[1], dropoff_node=nodes[2],
            revenue=100.0,        # Doanh thu nếu phục vụ được khách A
            early_pickup=0.0,     # Sớm nhất có thể đón lúc t=0
            late_pickup=50.0,     # Muộn nhất phải đón trước t=50, quá thì vi phạm
            service_time=1.0      # Thời gian phục vụ tại mỗi điểm đón/trả
        ),
        PassengerRequest(
            id=2, pickup_node=nodes[3], dropoff_node=nodes[4],
            revenue=80.0, early_pickup=0.0, late_pickup=50.0, service_time=1.0
        ),
    ]

    # Khai báo 2 yêu cầu Bưu kiện, có thêm early/late cho cả pickup lẫn dropoff và trọng lượng (weight)
    parcels = [
        ParcelRequest(
            id=1, pickup_node=nodes[5], dropoff_node=nodes[6],
            revenue=60.0, weight=3.0,   # Hàng C nặng 3kg
            early_pickup=0.0, late_pickup=50.0,
            early_dropoff=0.0, late_dropoff=50.0, service_time=1.0
        ),
        ParcelRequest(
            id=2, pickup_node=nodes[7], dropoff_node=nodes[8],
            revenue=40.0, weight=2.0,   # Hàng D nặng 2kg
            early_pickup=0.0, late_pickup=50.0,
            early_dropoff=0.0, late_dropoff=50.0, service_time=1.0
        ),
    ]

    # Khai báo 2 xe taxi, cùng xuất phát từ Depot (nodes[0]), sức chứa bưu kiện tối đa = 5
    taxis = [
        Taxi(id=1, depot_node=nodes[0], capacity=5.0),
        Taxi(id=2, depot_node=nodes[0], capacity=5.0),
    ]
 
    # Gói toàn bộ dữ liệu (xe, khách, hàng, 2 ma trận) vào 1 đối tượng ProblemInstance
    return ProblemInstance(
        taxis=taxis, passengers=passengers, parcels=parcels,
        time_matrix=time_matrix, cost_matrix=cost_matrix
    )

def print_node_table(instance: ProblemInstance):
    """In ra bảng liệt kê toàn bộ node đang có trong instance, để dễ đối chiếu id <-> loại node."""
    print("Bảng các Node trong dữ liệu demo:")
    print(f"{'id':>3} {'type':<18} {'matrix_index':>12}")
 
    # Gom tất cả node lại thành 1 danh sách: depot + (pickup, dropoff) của từng khách/hàng
    all_nodes = [instance.taxis[0].depot_node]
    for p in instance.passengers:
        all_nodes += [p.pickup_node, p.dropoff_node]
    for h in instance.parcels:
        all_nodes += [h.pickup_node, h.dropoff_node]
 
    # In từng dòng: id node, loại node, chỉ số trong ma trận (matrix_index)
    for node in all_nodes:
        print(f"{node.id:>3} {node.type:<18} {node.matrix_index:>12}")

# 2: Test utils.py

def demo_utils(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO utils.py")
    print("-" * 60)

    # --- get_spatial_transition: tra cứu (cost, time) giữa 2 node ---
    u_idx, v_idx = 0, 1  # Depot -> Điểm đón khách A
    cost, t = get_spatial_transition(u_idx, v_idx, instance.cost_matrix, instance.time_matrix)
    print(f"get_spatial_transition(Depot -> P_A): cost={cost}, time={t}")

    # --- calculate_next_time: tính mốc thời gian đến/phục vụ/rời điểm P_A ---
    early_v, late_v, service_v = instance.get_node_time_windows(instance.passengers[0].pickup_node)
    result = calculate_next_time(
        dep_u=0.0, u_idx=u_idx, v_idx=v_idx, time_matrix=instance.time_matrix,
        early_v=early_v, late_v=late_v, service_v=service_v
    )
    if result:
        arr_v, srv_v, dep_v = result
        print(f"calculate_next_time(Depot -> P_A): arrival={arr_v}, start_service={srv_v}, departure={dep_v}")
    else:
        print("calculate_next_time: đến muộn hơn late_pickup -> vi phạm (trả về None)")

    # --- calculate_next_load: cộng tải khi lấy bưu kiện C (weight=3) trên xe capacity=5 ---
    new_load = calculate_next_load(
        current_load=0.0, node_type='PARCEL_PICKUP',
        weight=instance.parcels[0].weight, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (lấy hàng C, weight=3, capacity=5): load mới = {new_load}")

    # --- thử lấy thêm hàng D (weight=2) -> tổng 5, vẫn vừa đủ ---
    new_load_2 = calculate_next_load(
        current_load=new_load, node_type='PARCEL_PICKUP',
        weight=instance.parcels[1].weight, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (lấy thêm hàng D, weight=2): load mới = {new_load_2}")

    # --- thử vi phạm: lấy thêm 1kg nữa (giả lập) sẽ vượt capacity=5 -> trả về None ---
    overload = calculate_next_load(
        current_load=new_load_2, node_type='PARCEL_PICKUP',
        weight=1.0, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (thử lấy thêm 1kg khi đã đầy 5/5): kết quả = {overload}  (None nghĩa là vi phạm)")


# 3: Test validator.py trên 1 lộ trình hợp lệ và 1 lộ trình không hợp lệ

def demo_validator(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO validator.py")
    print("-" * 60)

    taxi = instance.taxis[0]
    p_a = instance.passengers[0]   # nodes 1, 2
    h_c = instance.parcels[0]      # nodes 5, 6

    # Lộ trình hợp lệ: đón/trả khách A liền kề, rồi lấy/giao hàng C 
    good_route = Route(taxi=taxi, stops=[
        p_a.pickup_node, p_a.dropoff_node, h_c.pickup_node, h_c.dropoff_node
    ])
    print("Lộ trình hợp lệ: Depot -> P_A -> D_A -> P_C -> D_C")
    print(f"  validate_spatial_flow          = {validate_spatial_flow(good_route, instance)}")
    print(f"  validate_temporal_flow         = {validate_temporal_flow(good_route, instance)}")
    print(f"  validate_capacity_flow         = {validate_capacity_flow(good_route, instance)}")
    print(f"  validate_direct_passenger_flow = {validate_direct_passenger_flow(good_route, instance)}")
    print(f"  is_route_valid (gộp cả 4)      = {is_route_valid(good_route, instance)}")

    # Lộ trình vi phạm: chèn 1 điểm khác xen giữa đón/trả khách A (phá vỡ Công thức 7)
    bad_route = Route(taxi=taxi, stops=[
        p_a.pickup_node, h_c.pickup_node, p_a.dropoff_node, h_c.dropoff_node
    ])
    print("\nLộ trình VI PHẠM: Depot -> P_A -> P_C -> D_A -> D_C  (ghé P_C xen giữa đón/trả khách A)")
    print(f"  validate_direct_passenger_flow = {validate_direct_passenger_flow(bad_route, instance)}  (False = đúng như kỳ vọng)")
    print(f"  is_route_valid (gộp cả 4)      = {is_route_valid(bad_route, instance)}")

    # --- Lộ trình vi phạm tải trọng: giả lập taxi sức chứa nhỏ ---
    small_taxi = Taxi(id=99, depot_node=taxi.depot_node, capacity=2.0)  # nhỏ hơn weight hàng C=3
    overload_route = Route(taxi=small_taxi, stops=[h_c.pickup_node, h_c.dropoff_node])
    print("\nLộ trình VI PHẠM tải trọng: xe capacity=2 nhưng hàng C nặng 3")
    print(f"  validate_capacity_flow = {validate_capacity_flow(overload_route, instance)}  (False = đúng như kỳ vọng)")


# 4: Test greedy_solver.py xem từng bước chèn

def demo_greedy_solver(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO greedy_solver.py")
    print("-" * 60)

    solver = GreedySolver(instance)

    # Gọi trực tiếp 2 hàm tìm-vị-trí-chèn-tốt-nhất TRƯỚC khi solve(),
    # để xem thuật toán "nhìn thấy" gì ở bước đầu tiên.
    pass_req, p_taxi, p_pos, p_gain = solver.find_best_passenger_insertion()
    print(f"Bước đầu - chèn khách tốt nhất: request={pass_req.id if pass_req else None}, "
          f"taxi_idx={p_taxi}, vị trí={p_pos}, gain={p_gain:.2f}")

    parcel_req, r_taxi, r_i, r_j, r_gain = solver.find_best_parcel_insertion()
    print(f"Bước đầu - chèn hàng tốt nhất:  request={parcel_req.id if parcel_req else None}, "
          f"taxi_idx={r_taxi}, vị trí lấy={r_i}, vị trí giao={r_j}, gain={r_gain:.2f}")

    # Chạy toàn bộ vòng lặp solve()
    routes = solver.solve()

    print("\nKết quả cuối cùng của GreedySolver:")
    for route in routes:
        stop_ids = [s.id for s in route.stops]
        print(f"  Taxi {route.taxi.id}: Depot -> {stop_ids}")

    obj = calculate_objective_value(routes, instance)
    print(f"\nTổng lợi nhuận (Greedy) = {obj:.2f}")
    return routes, obj



# 5: Test random_solver.py để so sánh

def demo_random_solver(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO random_solver.py")
    print("-" * 60)

    solver = RandomSolver(instance, seed=1)
    routes = solver.solve()

    print("Kết quả của RandomSolver:")
    for route in routes:
        stop_ids = [s.id for s in route.stops]
        print(f"  Taxi {route.taxi.id}: Depot -> {stop_ids}")

    obj = calculate_objective_value(routes, instance)
    print(f"\nTổng lợi nhuận (Random) = {obj:.2f}")
    return routes, obj

# 5b: Test hill_climbing.py (dùng _mock_relocate_operator, chưa có operators.py của Hà Thu)

def demo_hill_climbing(instance: ProblemInstance):
    """
    Chạy HillClimbingSolver trên nền lời giải cơ sở của GreedySolver, dùng
    _mock_relocate_operator (ngẫu nhiên) làm toán tử sinh hàng xóm tạm thời,
    vì operators.py (relocate/swap thật) của Hà Thu chưa có.
    Mục đích: kiểm chứng vòng lặp Hill Climbing + evaluator.py không crash,
    và benefit sau khi chạy không bao giờ TỆ HƠN benefit trước khi chạy
    (vì thuật toán chỉ accept khi delta_benefit > 0).
    """
    print("\n" + "-" * 60)
    print("DEMO hill_climbing.py")
    print("-" * 60)

    # 1. Lấy lời giải cơ sở từ GreedySolver làm điểm khởi đầu
    greedy_solver = GreedySolver(instance)
    greedy_routes = greedy_solver.solve()
    benefit_before = calculate_objective_value(greedy_routes, instance)

    print("Lộ trình TRƯỚC Hill Climbing (từ Greedy):")
    for route in greedy_routes:
        print(f"  Taxi {route.taxi.id}: Depot -> {[s.id for s in route.stops]}")
    print(f"Benefit TRƯỚC = {benefit_before:.2f}")

    # 2. HillClimbingSolver nhận vào List[List[Node]], không phải List[Route],
    #    nên phải tách .stops ra trước khi truyền vào.
    initial_routes = [route.stops for route in greedy_routes]

    random.seed(7)  # cố định seed để chạy lại tái lập được kết quả khi debug
    hc_solver = HillClimbingSolver(instance, initial_routes)
    final_stops_list = hc_solver.solve()

    # 3. Đóng gói lại thành Route (giữ nguyên taxi tương ứng theo thứ tự) để
    #    tính lại benefit bằng đúng hàm calculate_objective_value dùng chung.
    final_routes = [
        Route(taxi=greedy_routes[i].taxi, stops=final_stops_list[i])
        for i in range(len(greedy_routes))
    ]
    benefit_after = calculate_objective_value(final_routes, instance)

    print("\nLộ trình SAU Hill Climbing:")
    for route in final_routes:
        print(f"  Taxi {route.taxi.id}: Depot -> {[s.id for s in route.stops]}")
    print(f"Benefit SAU  = {benefit_after:.2f}")

    # 4. Cảnh báo tự động nếu benefit bị TỆ HƠN sau khi "tối ưu" -> có nghĩa là
    #    evaluator.py hoặc vòng lặp accept/reject đang có bug logic.
    if benefit_after < benefit_before - 1e-6:
        print("[CẢNH BÁO] Benefit SAU < Benefit TRƯỚC -> có bug trong logic accept của Hill Climbing!")
    else:
        print("Benefit không giảm sau Hill Climbing -> logic accept/reject ổn (dùng mock operator).")

    return final_routes, benefit_after


# 5c: Test riêng evaluator.py (calculate_delta_cost / check_capacity_delta),
#     đặc biệt case bưu kiện TÁCH RỜI (pickup và dropoff không nằm liền kề nhau)

def demo_evaluator(instance: ProblemInstance):
    """
    calculate_delta_cost() trong evaluator.py chỉ tính delta cho việc chèn
    ĐÚNG 1 node giữa 2 node A, B. Với bưu kiện tách rời (pickup ở vị trí i,
    dropoff ở vị trí j > i, có thể có các điểm khác chen giữa), phải gọi
    hàm này 2 LẦN riêng biệt (1 lần cho điểm chèn pickup, 1 lần cho điểm
    chèn dropoff) rồi CỘNG LẠI - giống đúng cách get_parcel_delta_cost()
    trong greedy_solver.py làm ở nhánh i != j.

    Test này dựng 1 route có sẵn, chèn 1 bưu kiện mới TÁCH RỜI vào, rồi so
    delta_cost tính bằng evaluator.calculate_delta_cost (gọi 2 lần, cộng
    lại) với cách tính "từ đầu" (get_route_cost kiểu greedy_solver) để chắc
    2 cách cho cùng kết quả.
    """
    print("\n" + "-" * 60)
    print("DEMO evaluator.py - case bưu kiện tách rời")
    print("-" * 60)

    cost_mat = instance.cost_matrix
    taxi = instance.taxis[0]

    # Route có sẵn (đã hợp lệ, không tính đơn mới): P_A -> D_A -> P_C -> D_C
    p_a, h_c = instance.passengers[0], instance.parcels[0]
    stops = [p_a.pickup_node, p_a.dropoff_node, h_c.pickup_node, h_c.dropoff_node]

    def route_cost(depot, stop_list):
        if not stop_list:
            return 0.0
        c = cost_mat[depot.matrix_index][stop_list[0].matrix_index]
        for k in range(len(stop_list) - 1):
            c += cost_mat[stop_list[k].matrix_index][stop_list[k + 1].matrix_index]
        return c

    old_cost = route_cost(taxi.depot_node, stops)

    # Bưu kiện thứ 2 (parcel[1], node 7-8) sẽ được chèn TÁCH RỜI:
    # pickup vào vị trí i=1 (giữa D_A và P_C), dropoff vào vị trí j=3
    # (giữa D_C và cuối route) -> có 2 điểm dừng khác (P_C, D_C) nằm
    # giữa pickup và dropoff của bưu kiện mới, đúng nghĩa "tách rời".
    h_d = instance.parcels[1]
    i, j = 1, 3
    new_stops = stops[:i] + [h_d.pickup_node] + stops[i:j] + [h_d.dropoff_node] + stops[j:]
    new_cost_bruteforce = route_cost(taxi.depot_node, new_stops)
    delta_cost_bruteforce = new_cost_bruteforce - old_cost

    # --- Cách tính bằng evaluator.calculate_delta_cost, gọi 2 lần rồi cộng ---
    # Điểm chèn pickup: A = node liền trước vị trí i (ở mảng CŨ), B = node đang ở vị trí i
    A1 = stops[i - 1] if i > 0 else taxi.depot_node
    B1 = stops[i]
    delta_pickup = calculate_delta_cost(A1, B1, h_d.pickup_node, cost_mat)

    # Điểm chèn dropoff: C = node liền trước vị trí j (ở mảng CŨ), D_next = node đang ở vị trí j
    C1 = stops[j - 1]
    D_next1 = stops[j] if j < len(stops) else None
    if D_next1 is not None:
        delta_dropoff = calculate_delta_cost(C1, D_next1, h_d.dropoff_node, cost_mat)
    else:
        # Chèn ở cuối route -> không có cạnh (C, D_next) để "xóa", chỉ có cạnh (C, dropoff) mới
        delta_dropoff = cost_mat[C1.matrix_index][h_d.dropoff_node.matrix_index]

    delta_cost_evaluator = delta_pickup + delta_dropoff

    print(f"Route cũ: Depot -> {[s.id for s in stops]}  (cost = {old_cost:.2f})")
    print(f"Chèn tách rời bưu kiện D: pickup tại vị trí {i}, dropoff tại vị trí {j}")
    print(f"Route mới: Depot -> {[s.id for s in new_stops]}  (cost = {new_cost_bruteforce:.2f})")
    print(f"Delta cost (tính lại từ đầu)         = {delta_cost_bruteforce:.4f}")
    print(f"Delta cost (evaluator, gọi 2 lần)    = {delta_cost_evaluator:.4f}")
    match = abs(delta_cost_bruteforce - delta_cost_evaluator) < 1e-6
    print(f"=> {'KHỚP' if match else 'LỆCH -> CÓ BUG!'}")

    # --- Test check_capacity_delta với case tách rời: phát hiện hạn chế của hàm ---
    # check_capacity_delta CHỈ nhận 1 insert_idx (điểm pickup), KHÔNG có tham số
    # nào cho biết dropoff nằm ở đâu -> nó cộng "weight" vào TOÀN BỘ các điểm dừng
    # từ insert_idx đến HẾT route, coi như bưu kiện không bao giờ được giao (tệ nhất).
    # Với bưu kiện tách rời (dropoff nằm giữa route, không phải cuối), cách tính này
    # có thể từ chối 1 phương án chèn HOÀN TOÀN HỢP LỆ, chỉ vì tải trọng CŨ (không
    # liên quan gì đến bưu kiện mới) ở phía sau điểm dropoff vốn đã cao sẵn.
    print("\n--- Test check_capacity_delta với case tách rời (phát hiện hạn chế) ---")
    capacity = 4.0  # cố ý đặt thấp hơn h_c.weight(3) + h_d.weight(2) = 5, để lộ rõ hạn chế
    # current_loads mô phỏng: tải trọng CŨ (trước khi chèn) sau mỗi điểm dừng của route gốc
    # (route gốc gồm 4 stop: P_A, D_A, P_C, D_C -> không có bưu kiện nào trên xe ở 2 stop đầu,
    # có bưu kiện h_c (weight=3) từ stop index2 (P_C) đến hết vì D_C là stop cuối)
    current_loads = [0.0, 0.0, h_c.weight, 0.0]  # load sau mỗi stop: [P_A, D_A, P_C, D_C]

    # Giả sử bưu kiện D (weight=2) được chèn pickup ở vị trí i=1, và dropoff ngay
    # sau đó ở vị trí 2 (TRƯỚC khi chạm P_C) -> cửa sổ mang hàng D rất ngắn, không
    # hề chồng với lúc xe đang chở hàng C (index2-3) -> phải HỢP LỆ.
    is_valid = check_capacity_delta(
        route_stops=stops, insert_idx=1, insert_node=h_d.pickup_node,
        capacity=capacity, current_loads=current_loads, weight=h_d.weight
    )
    print(f"Chèn pickup D (weight={h_d.weight}) tại vị trí 1, dropoff ngay sau (không chạm hàng C):")
    print(f"  check_capacity_delta trả về = {is_valid}")
    print(f"  (Load thực tế tại các vị trí sau đó: index2 có h_c.weight={h_c.weight} sẵn trên xe,")
    print(f"   nếu hàm cộng thêm weight={h_d.weight} vào TẤT CẢ vị trí phía sau (kể cả sau khi D đã")
    print(f"   được giao) thì {h_c.weight}+{h_d.weight}={h_c.weight + h_d.weight} so với capacity={capacity}"
          f" -> {'VƯỢT' if h_c.weight + h_d.weight > capacity else 'không vượt'})")
    if not is_valid and h_c.weight + h_d.weight > capacity:
        print("  => XÁC NHẬN HẠN CHẾ: hàm từ chối phương án này dù nó hợp lệ trong thực tế,")
        print("     vì không biết bưu kiện D đã được giao (dropoff) TRƯỚC khi xe chạm hàng C.")
        print("     Cần thêm tham số 'dropoff_idx' để hàm chỉ cộng weight trong đúng khoảng")
        print("     [insert_idx, dropoff_idx), không cộng tới hết route.")


# 5d: Test riêng calculate_delta_time() bằng số liệu TỰ TAY dựng (không phụ thuộc
#     dữ liệu demo ngẫu nhiên), để có thể dò lại từng bước bằng tay/máy tính.

def demo_evaluator_delta_time():
    """
    Dựng 1 mini ProblemInstance CHỈ để test calculate_delta_time():
      - 1 depot O (matrix_index 0)
      - node A (matrix_index 1): parcel pickup của bưu kiện P1, window [0, 100]
      - node B (matrix_index 2): parcel dropoff của bưu kiện P1, window [0, 100]
      - node X (matrix_index 3): parcel pickup của bưu kiện P2 - node sẽ được CHÈN
        giữa A và B, window [0, 20] hoặc [0, 6] tùy case test

    Ma trận thời gian t(u, v) tự chọn (không đối xứng, đúng tinh thần đề bài):
        t(O,A)=5   t(O,B)=10  t(O,X)=7
        t(A,B)=4   t(A,X)=3
        t(B,X)=6

    ---- Case 1: X có window rộng [0, 20] -> chèn hợp lệ ----
    Tính TAY (theo đúng công thức 2,3,4 trong đề bài):
      dep_A (route CŨ, Depot->A->B): arr_A = 0 + t(O,A) = 5
                                      srv_A = max(5, E_A=0) = 5 ; dep_A = 5 + S_A(0) = 5
      old_dep_B (route CŨ): arr_B = dep_A + t(A,B) = 5 + 4 = 9
                             srv_B = max(9, 0) = 9 ; old_dep_B = 9 + 0 = 9

      Chèn X giữa A và B (route MỚI: Depot->A->X->B):
      arr_X = dep_A + t(A,X) = 5 + 3 = 8   (<= late_X=20, HỢP LỆ)
      srv_X = max(8, E_X=0) = 8 ; dep_X = 8 + S_X(2) = 10
      arr_B_new = dep_X + t(X,B) = 10 + 6 = 16   (<= late_B=100, HỢP LỆ)
      srv_B_new = max(16, 0) = 16 ; dep_B_new = 16 + 0 = 16

      => delta_time (TAY) = dep_B_new - old_dep_B = 16 - 9 = 7

    ---- Case 2: X có window hẹp [0, 6] -> arr_X = 8 > late_X = 6 -> PHẢI trả về None ----
    """
    print("\n" + "-" * 60)
    print("DEMO evaluator.py - test calculate_delta_time() bằng số liệu tay")
    print("-" * 60)

    depot = Node(id=0, type='DEPOT', matrix_index=0)
    node_A = Node(id=1, type='PARCEL_PICKUP', matrix_index=1)
    node_B = Node(id=2, type='PARCEL_DROPOFF', matrix_index=2)
    node_X = Node(id=3, type='PARCEL_PICKUP', matrix_index=3)

    parcel_1 = ParcelRequest(
        id=1, pickup_node=node_A, dropoff_node=node_B, revenue=0.0,
        early_pickup=0.0, late_pickup=100.0,
        early_dropoff=0.0, late_dropoff=100.0,
        service_time=0.0, weight=0.0,
    )

    INF = float('inf')
    #        O    A    B    X
    time_matrix = [
        [0.0, 5.0, 10.0, 7.0],   # từ O
        [5.0, 0.0, 4.0, 3.0],    # từ A  (t(A,B)=4, t(A,X)=3)
        [10.0, 4.0, 0.0, 6.0],   # từ B  (t(B,X)=6, và QUAN TRỌNG: t(X,B) cũng phải =6 ở dòng dưới)
        [7.0, 3.0, 6.0, 0.0],    # từ X  (t(X,B)=6 <- nếu để INF ở đây, calculate_delta_time sẽ luôn trả None)
    ]
    cost_matrix = [row[:] for row in time_matrix]  # cost không dùng trong test này, copy tạm

    taxi = Taxi(id=1, depot_node=depot, capacity=100.0)

    dep_A = 5.0       # tính tay ở trên
    old_dep_B = 9.0    # tính tay ở trên

    # --- Case 1: window rộng [0, 20] -> phải chèn được, delta = 7 ---
    parcel_2_wide = ParcelRequest(
        id=2, pickup_node=node_X, dropoff_node=node_X, revenue=0.0,
        early_pickup=0.0, late_pickup=20.0,
        early_dropoff=0.0, late_dropoff=20.0,
        service_time=2.0, weight=0.0,
    )
    instance_wide = ProblemInstance(
        taxis=[taxi], passengers=[], parcels=[parcel_1, parcel_2_wide],
        time_matrix=time_matrix, cost_matrix=cost_matrix,
    )
    delta_case1 = calculate_delta_time(
        dep_A=dep_A, node_A=node_A, node_B=node_B,
        old_dep_B=old_dep_B, insert_node=node_X, instance=instance_wide,
    )
    print(f"Case 1 (window X = [0, 20]): calculate_delta_time trả về = {delta_case1}")
    print(f"  Kỳ vọng (tính tay) = 7.0  ->  {'KHỚP' if delta_case1 is not None and abs(delta_case1 - 7.0) < 1e-6 else 'LỆCH -> CÓ BUG!'}")

    # --- Case 2: window hẹp [0, 6] -> arr_X = 8 > late_X = 6 -> phải trả về None ---
    parcel_2_tight = ParcelRequest(
        id=2, pickup_node=node_X, dropoff_node=node_X, revenue=0.0,
        early_pickup=0.0, late_pickup=6.0,
        early_dropoff=0.0, late_dropoff=6.0,
        service_time=2.0, weight=0.0,
    )
    instance_tight = ProblemInstance(
        taxis=[taxi], passengers=[], parcels=[parcel_1, parcel_2_tight],
        time_matrix=time_matrix, cost_matrix=cost_matrix,
    )
    delta_case2 = calculate_delta_time(
        dep_A=dep_A, node_A=node_A, node_B=node_B,
        old_dep_B=old_dep_B, insert_node=node_X, instance=instance_tight,
    )
    print(f"Case 2 (window X = [0, 6]):  calculate_delta_time trả về = {delta_case2}")
    print(f"  Kỳ vọng (tính tay) = None (arr_X=8 > late_X=6)  ->  {'KHỚP' if delta_case2 is None else 'LỆCH -> CÓ BUG!'}")


# 6: Sinh dữ liệu lớn

def generate_random_instance(
    n_passengers: int,
    n_parcels: int,
    n_taxis: int,
    seed: int = 42
) -> ProblemInstance:
    """Sinh dữ liệu giả lập có quy mô tùy chỉnh."""
    random.seed(seed)

    nodes = [Node(id=0, type='DEPOT', matrix_index=0)]
    node_idx = 1

    passengers = []
    parcels = []

    for i in range(1, n_passengers + 1):
        p_node = Node(id=node_idx, type='PASSENGER_PICKUP', matrix_index=node_idx)
        node_idx += 1
        d_node = Node(id=node_idx, type='PASSENGER_DROPOFF', matrix_index=node_idx)
        node_idx += 1
        nodes.extend([p_node, d_node])

        passengers.append(PassengerRequest(
            id=i, pickup_node=p_node, dropoff_node=d_node,
            revenue=100.0, early_pickup=0.0, late_pickup=1000.0, service_time=2.0
        ))

    for j in range(1, n_parcels + 1):
        p_node = Node(id=node_idx, type='PARCEL_PICKUP', matrix_index=node_idx)
        node_idx += 1
        d_node = Node(id=node_idx, type='PARCEL_DROPOFF', matrix_index=node_idx)
        node_idx += 1
        nodes.extend([p_node, d_node])

        parcels.append(ParcelRequest(
            id=j, pickup_node=p_node, dropoff_node=d_node,
            weight=2.0, revenue=50.0, early_pickup=0.0, late_pickup=1000.0,
            early_dropoff=0.0, late_dropoff=1000.0, service_time=1.0
        ))

    taxis = [Taxi(id=k, depot_node=nodes[0], capacity=10.0) for k in range(1, n_taxis + 1)]

    total_nodes = len(nodes)
    cost_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]
    time_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]

    for r in range(total_nodes):
        for c in range(total_nodes):
            if r != c:
                val = float(random.randint(5, 25))
                cost_matrix[r][c] = val
                time_matrix[r][c] = val / 2.0

    return ProblemInstance(
        taxis=taxis, passengers=passengers, parcels=parcels,
        time_matrix=time_matrix, cost_matrix=cost_matrix
    )


def run_benchmark():
    test_cases = [
        {"name": "Nhỏ (Small)", "passengers": 10, "parcels": 10, "taxis": 3},
        {"name": "Vừa (Medium)", "passengers": 20, "parcels": 20, "taxis": 5},
        {"name": "Lớn (Large)", "passengers": 35, "parcels": 35, "taxis": 8},
    ]

    print("\n" + "-" * 60)
    print("BẮT ĐẦU BENCHMARK GREEDY SOLVER (dữ liệu lớn, ngẫu nhiên)")
    print("-" * 60)
    for case in test_cases:
        p, h, t = case["passengers"], case["parcels"], case["taxis"]
        instance = generate_random_instance(n_passengers=p, n_parcels=h, n_taxis=t)

        start_time = time.time()
        solver = GreedySolver(instance)
        routes = solver.solve()
        elapsed_time = time.time() - start_time

        benefit = calculate_objective_value(routes, instance)
        total_stops = sum(len(r.stops) for r in routes)

        print(f"--- Kịch bản: {case['name']} ({p} Khách, {h} Hàng, {t} Xe) ---")
        print(f"Thời gian chạy: {elapsed_time:.4f} giây")
        print(f"Tổng Lợi Nhuận: {benefit:.2f}")
        print(f"Tổng số điểm dừng đã chèn thành công: {total_stops}/{2 * (p + h)}")
        print("-" * 50)


# Main
def main():
    print("TẠO DỮ LIỆU MẪU NHỎ (2 khách, 2 bưu kiện, 2 xe)")
    instance = generate_demo_instance()
    print_node_table(instance)

    demo_utils(instance)
    demo_validator(instance)
    demo_greedy_solver(instance)
    demo_random_solver(instance)
    demo_hill_climbing(instance)
    demo_evaluator(instance)
    demo_evaluator_delta_time()

    run_benchmark()


if __name__ == "__main__":
    main()