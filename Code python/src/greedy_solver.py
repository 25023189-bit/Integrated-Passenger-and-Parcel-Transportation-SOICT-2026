from typing import List, Optional, Tuple
from models import ProblemInstance, Route, PassengerRequest, ParcelRequest, Node
from validator import is_route_valid

class GreedySolver:
    def __init__(self, instance: ProblemInstance):
        self.instance = instance
        self.routes = [Route(taxi=taxi) for taxi in instance.taxis]
        self.unserved_passengers = set(instance.passengers)
        self.unserved_parcels = set(instance.parcels)

    def get_route_cost(self, route: Route) -> float:
        """Tính tổng chi phí di chuyển thực tế của một lộ trình."""
        stops = route.stops
        if not stops:
            return 0.0
        cost_mat = self.instance.cost_matrix
        cost = cost_mat[route.taxi.depot_node.matrix_index][stops[0].matrix_index]
        for idx in range(len(stops) - 1):
            cost += cost_mat[stops[idx].matrix_index][stops[idx + 1].matrix_index]
        return cost

    def get_passenger_delta_cost(self, route: Route, p_node: Node, d_node: Node, pos: int) -> float:
        """
        [Tối ưu O(1)]: Tính Delta Cost khi chèn liên tiếp [Pickup, Dropoff] của Hành khách vào vị trí pos.
        """
        stops = route.stops
        cost_mat = self.instance.cost_matrix
        
        # Xác định 2 nút kề bên vị trí chèn
        A = stops[pos - 1] if pos > 0 else route.taxi.depot_node
        B = stops[pos] if pos < len(stops) else None
        
        # Tính chi phí cạnh cũ bị xóa và các cạnh mới được thêm vào
        cost_removed = 0.0 if B is None else cost_mat[A.matrix_index][B.matrix_index]
        cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] + 
                      cost_mat[p_node.matrix_index][d_node.matrix_index])
        if B is not None:
            cost_added += cost_mat[d_node.matrix_index][B.matrix_index]
            
        return cost_added - cost_removed

    def get_parcel_delta_cost(self, route: Route, p_node: Node, d_node: Node, i: int, j: int) -> float:
        """
        [Tối ưu O(1)]: Tính Delta Cost khi chèn Pickup tại vị trí i và Dropoff tại vị trí j (trong mảng ban đầu).
        """
        stops = route.stops
        cost_mat = self.instance.cost_matrix
        
        if i == j: # Trường hợp chèn liền kề nhau
            A = stops[i - 1] if i > 0 else route.taxi.depot_node
            B = stops[i] if i < len(stops) else None
            
            cost_removed = 0.0 if B is None else cost_mat[A.matrix_index][B.matrix_index]
            cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] + 
                          cost_mat[p_node.matrix_index][d_node.matrix_index])
            if B is not None:
                cost_added += cost_mat[d_node.matrix_index][B.matrix_index]
            return cost_added - cost_removed
            
        else: # Trường hợp chèn tách rời (i < j)
            # Tại điểm Pickup (vị trí i)
            A = stops[i - 1] if i > 0 else route.taxi.depot_node
            B = stops[i] 
            
            # Tại điểm Dropoff (vị trí j trong mảng ban đầu)
            C = stops[j - 1] 
            D_next = stops[j] if j < len(stops) else None
            
            cost_removed = cost_mat[A.matrix_index][B.matrix_index]
            cost_added = (cost_mat[A.matrix_index][p_node.matrix_index] + 
                          cost_mat[p_node.matrix_index][B.matrix_index])
            
            if D_next is not None:
                cost_removed += cost_mat[C.matrix_index][D_next.matrix_index]
                cost_added += (cost_mat[C.matrix_index][d_node.matrix_index] + 
                               cost_mat[d_node.matrix_index][D_next.matrix_index])
            else:
                cost_added += cost_mat[C.matrix_index][d_node.matrix_index]
                
            return cost_added - cost_removed

    def find_best_passenger_insertion(self) -> Tuple[Optional[PassengerRequest], Optional[int], Optional[int], float]:
        """Tìm vị trí chèn hành khách cho lợi nhuận tăng thêm Delta Benefit lớn nhất."""
        best_req, best_taxi_idx, best_pos, max_gain = None, None, None, 0.0

        for req in self.unserved_passengers:
            nodes = [req.pickup_node, req.dropoff_node]
            for t_idx, route in enumerate(self.routes):
                for i in range(len(route.stops) + 1):
                    # Chèn cặp [Pickup, Dropoff] liền kề để bảo toàn luồng khách đi thẳng (Công thức 7)
                    temp_stops = route.stops[:i] + nodes + route.stops[i:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    if is_route_valid(temp_route, self.instance):
                        delta_cost = self.get_passenger_delta_cost(route, req.pickup_node, req.dropoff_node, i)
                        gain = req.revenue - delta_cost
                        if gain > max_gain:
                            max_gain = gain
                            best_req, best_taxi_idx, best_pos = req, t_idx, i

        return best_req, best_taxi_idx, best_pos, max_gain

    def find_best_parcel_insertion(self) -> Tuple[Optional[ParcelRequest], Optional[int], Optional[int], Optional[int], float]:
        """
        Tìm vị trí chèn bưu kiện (pickup ở pos_i, dropoff ở pos_j với pos_i <= pos_j)
        cho lợi nhuận tăng thêm Delta Benefit lớn nhất.
        """
        best_req, best_taxi_idx, best_i, best_j, max_gain = None, None, None, None, 0.0

        for req in self.unserved_parcels:
            p_node, d_node = req.pickup_node, req.dropoff_node
            for t_idx, route in enumerate(self.routes):
                n = len(route.stops)
                for i in range(n + 1):
                    for j in range(i, n + 1):
                        # Chèn Pickup tại i và Dropoff tại j (sau khi đã chèn i)
                        temp_stops = route.stops[:i] + [p_node] + route.stops[i:j] + [d_node] + route.stops[j:]
                        temp_route = Route(taxi=route.taxi, stops=temp_stops)

                        if is_route_valid(temp_route, self.instance):
                            delta_cost = self.get_parcel_delta_cost(route, p_node, d_node, i, j)
                            gain = req.revenue - delta_cost
                            if gain > max_gain:
                                max_gain = gain
                                best_req, best_taxi_idx, best_i, best_j = req, t_idx, i, j

        return best_req, best_taxi_idx, best_i, best_j, max_gain

    def solve(self) -> List[Route]:
        """Vòng lặp Greedy chèn đơn cho đến khi không còn đơn nào (khách hoặc bưu kiện) giúp tăng Benefit."""
        while True:
            # 1. Tìm phương án chèn tốt nhất cho Hành khách và Bưu kiện
            pass_req, p_taxi, p_pos, p_gain = self.find_best_passenger_insertion()
            parcel_req, r_taxi, r_i, r_j, r_gain = self.find_best_parcel_insertion()

            # 2. So sánh và thực hiện chèn phương án có Gain lớn nhất (> 0)
            if p_gain > 0 and p_gain >= r_gain:
                nodes = [pass_req.pickup_node, pass_req.dropoff_node]
                self.routes[p_taxi].stops = (
                    self.routes[p_taxi].stops[:p_pos] + nodes + self.routes[p_taxi].stops[p_pos:]
                )
                self.unserved_passengers.remove(pass_req)

            elif r_gain > 0 and r_gain > p_gain:
                p_node, d_node = parcel_req.pickup_node, parcel_req.dropoff_node
                self.routes[r_taxi].stops = (
                    self.routes[r_taxi].stops[:r_i] + [p_node] + self.routes[r_taxi].stops[r_i:r_j] + [d_node] + self.routes[r_taxi].stops[r_j:]
                )
                self.unserved_parcels.remove(parcel_req)

            else:
                # Ngắt vòng lặp khi không còn chèn thêm được đơn nào có lợi nhuận dương
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
            continue
        
        # 1. Chi phí di chuyển của xe k
        cost_mat = instance.cost_matrix
        c_route = cost_mat[route.taxi.depot_node.matrix_index][route.stops[0].matrix_index]
        for idx in range(len(route.stops) - 1):
            c_route += cost_mat[route.stops[idx].matrix_index][route.stops[idx + 1].matrix_index]
        total_cost += c_route

        # 2. Doanh thu từ các đơn được phục vụ
        for node in route.stops:
            if node.type == 'PASSENGER_PICKUP':
                p = instance.get_passenger_by_node(node)
                if p: total_revenue += p.revenue
            elif node.type == 'PARCEL_PICKUP':
                h = instance.get_parcel_by_node(node)
                if h: total_revenue += h.revenue

    return total_revenue - total_cost