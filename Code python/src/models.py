from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict

@dataclass
class Node:
    """Đại diện cho một điểm trên bản đồ (v_r^k)"""
    id: int               
    type: str            
    matrix_index: int    

@dataclass
class PassengerRequest:
    """Yêu cầu Hành khách i (1 <= i <= N)"""
    id: int              
    pickup_node: Node     
    dropoff_node: Node   
    revenue: float      
    early_pickup: float  
    late_pickup: float   
    service_time: float    

@dataclass
class ParcelRequest:
    """Yêu cầu Bưu kiện j (1 <= j <= M)"""
    id: int             
    pickup_node: Node  
    dropoff_node: Node    
    revenue: float    
    early_pickup: float 
    late_pickup: float   
    early_dropoff: float
    late_dropoff: float 
    service_time: float 
    weight: float         

@dataclass
class Taxi:
    """Thông tin xe Taxi k (1 <= k <= K)"""
    id: int          
    depot_node: Node  
    capacity: float      

@dataclass
class Route:
    """Lộ trình R_k của một taxi k"""
    taxi: Taxi            
    stops: List[Node] = field(default_factory=list) 
    current_load: float = 0.0     
    current_time: float = 0.0    
    total_cost: float = 0.0     

@dataclass
class ProblemInstance:
    """Lưu trữ toàn bộ dữ liệu của một testcase""" 
    taxis: List[Taxi]
    passengers: List[PassengerRequest]
    parcels: List[ParcelRequest]
    time_matrix: List[List[float]] # Lưu t(u, v)
    cost_matrix: List[List[float]] # Lưu c(u, v)

    # Dictionary hỗ trợ tra cứu nhanh O(1) từ Node index sang Request
    _node_to_passenger: Dict[int, PassengerRequest] = field(default_factory=dict, init=False)
    _node_to_parcel: Dict[int, ParcelRequest] = field(default_factory=dict, init=False)

    def __post_init__(self):
        for p in self.passengers:
            self._node_to_passenger[p.pickup_node.matrix_index] = p
            self._node_to_passenger[p.dropoff_node.matrix_index] = p
        for h in self.parcels:
            self._node_to_parcel[h.pickup_node.matrix_index] = h
            self._node_to_parcel[h.dropoff_node.matrix_index] = h

    def get_passenger_by_node(self, node: Node) -> Optional[PassengerRequest]:
        """Tra cứu yêu cầu hành khách tương ứng với Node."""
        return self._node_to_passenger.get(node.matrix_index)

    def get_parcel_by_node(self, node: Node) -> Optional[ParcelRequest]:
        """Tra cứu yêu cầu bưu kiện tương ứng với Node."""
        return self._node_to_parcel.get(node.matrix_index)

    def get_node_time_windows(self, node: Node) -> Tuple[float, float, float]:
        """Trả về tuple (early_time, late_time, service_time) tương ứng với từng loại Node."""
        pass_req = self.get_passenger_by_node(node)
        if pass_req:
            return pass_req.early_pickup, pass_req.late_pickup, pass_req.service_time
        
        parcel_req = self.get_parcel_by_node(node)
        if parcel_req:
            if node.type == 'PARCEL_PICKUP':
                return parcel_req.early_pickup, parcel_req.late_pickup, parcel_req.service_time
            elif node.type == 'PARCEL_DROPOFF':
                return parcel_req.early_dropoff, parcel_req.late_dropoff, parcel_req.service_time

        return 0.0, float('inf'), 0.0