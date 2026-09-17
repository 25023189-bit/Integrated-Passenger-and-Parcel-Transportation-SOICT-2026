from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

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