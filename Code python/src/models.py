from dataclasses import dataclass, field
from typing import List, Optional

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