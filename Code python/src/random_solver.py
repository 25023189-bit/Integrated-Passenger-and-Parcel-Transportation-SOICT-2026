import random
from typing import List, Optional
from models import ProblemInstance, Route, PassengerRequest, ParcelRequest, Node
from validator import is_route_valid

class RandomSolver:
    """
    Thuật toán Random Insertion (Phương án dự phòng).
    Xáo trộn ngẫu nhiên thứ tự đơn và vị trí chèn, tự động bỏ qua các phương án vi phạm ràng buộc.
    """
    def __init__(self, instance: ProblemInstance, max_attempts: int = 50, seed: Optional[int] = None):
        self.instance = instance
        self.max_attempts = max_attempts
        if seed is not None:
            random.seed(seed)

    def _get_route_cost(self, route: Route) -> float:
        stops = route.stops
        if not stops:
            return 0.0
        cost_mat = self.instance.cost_matrix
        cost = cost_mat[route.taxi.depot_node.matrix_index][stops[0].matrix_index]
        for idx in range(len(stops) - 1):
            cost += cost_mat[stops[idx].matrix_index][stops[idx + 1].matrix_index]
        return cost

    def _calculate_delta_cost(self, route: Route, new_stops: List[Node]) -> float:
        old_cost = self._get_route_cost(route)
        temp_route = Route(taxi=route.taxi, stops=new_stops)
        return self._get_route_cost(temp_route) - old_cost

    def solve() -> List[Route]:
        routes = [Route(taxi=t) for t in self.instance.taxis]
        unserved_passengers = list(self.instance.passengers)
        unserved_parcels = list(self.instance.parcels)

        # Xáo trộn danh sách đơn hàng
        random.shuffle(unserved_passengers)
        random.shuffle(unserved_parcels)

        # 1. Chèn ngẫu nhiên Hành khách
        for req in unserved_passengers[:]:
            nodes = [req.pickup_node, req.dropoff_node]
            taxi_indices = list(range(len(routes)))
            random.shuffle(taxi_indices)

            inserted = False
            for t_idx in taxi_indices:
                route = routes[t_idx]
                n_stops = len(route.stops)
                positions = list(range(n_stops + 1))
                random.shuffle(positions)

                for pos in positions:
                    temp_stops = route.stops[:pos] + nodes + route.stops[pos:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    # Bỏ qua nếu vi phạm ràng buộc cứng
                    if not is_route_valid(temp_route, self.instance):
                        continue

                    # Bỏ qua nếu lợi nhuận không dương
                    delta_cost = self._calculate_delta_cost(route, temp_stops)
                    if req.revenue - delta_cost <= 0:
                        continue

                    # Thỏa mãn: Chèn thành công
                    routes[t_idx].stops = temp_stops
                    inserted = True
                    break

                if inserted:
                    break

        # 2. Chèn ngẫu nhiên Bưu kiện
        for req in unserved_parcels[:]:
            p_node, d_node = req.pickup_node, req.dropoff_node
            taxi_indices = list(range(len(routes)))
            random.shuffle(taxi_indices)

            inserted = False
            for t_idx in taxi_indices:
                route = routes[t_idx]
                n_stops = len(route.stops)

                # Tạo danh sách cặp (i, j) hợp lệ với i <= j
                candidate_pairs = [(i, j) for i in range(n_stops + 1) for j in range(i, n_stops + 1)]
                random.shuffle(candidate_pairs)

                for i, j in candidate_pairs:
                    temp_stops = route.stops[:i] + [p_node] + route.stops[i:j] + [d_node] + route.stops[j:]
                    temp_route = Route(taxi=route.taxi, stops=temp_stops)

                    # Bỏ qua nếu vi phạm ràng buộc cứng
                    if not is_route_valid(temp_route, self.instance):
                        continue

                    # Bỏ qua nếu lợi nhuận không dương
                    delta_cost = self._calculate_delta_cost(route, temp_stops)
                    if req.revenue - delta_cost <= 0:
                        continue

                    routes[t_idx].stops = temp_stops
                    inserted = True
                    break

                if inserted:
                    break

        return routes