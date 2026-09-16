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

    def calculate_delta_cost(self, route: Route, new_stops: List[Node]) -> float:
        """Tính chênh lệch chi phí di chuyển Delta c(u, v) giữa lộ trình mới và cũ."""
        old_cost = self.get_route_cost(route)
        temp_route = Route(taxi=route.taxi, stops=new_stops)
        new_cost = self.get_route_cost(temp_route)
        return new_cost - old_cost

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
                        delta_cost = self.calculate_delta_cost(route, temp_stops)
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
                            delta_cost = self.calculate_delta_cost(route, temp_stops)
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
    
    # [Tối ưu & Đảm bảo đúng luật]: Chèn đồng thời cặp [P_i^n, D_i^n] liên tiếp vào index
    # Lý do: Việc chèn 2 nút kề nhau đảm bảo v_{r+1}^k luôn luôn là D_i^n ngay khi vừa sinh lời giải
    new_stops = (
        current_stops[:insert_idx] + 
        [passenger_req.pickup_node, passenger_req.dropoff_node] + 
        current_stops[insert_idx:]
    )
    
    return new_stops