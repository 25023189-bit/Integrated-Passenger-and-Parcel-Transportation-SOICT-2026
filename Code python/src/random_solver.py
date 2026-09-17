import random
from typing import List, Optional
from models import ProblemInstance, Route, PassengerRequest, ParcelRequest, Node
from validator import is_route_valid

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