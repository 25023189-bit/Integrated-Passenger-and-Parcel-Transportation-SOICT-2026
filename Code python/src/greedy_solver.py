from typing import List, Optional, Tuple
from models import ProblemInstance, Route, PassengerRequest, ParcelRequest, Node
from validator import is_route_valid

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
        """
        best_req, best_taxi_idx, best_i, best_j, max_gain = None, None, None, None, 0.0

        for req in self.unserved_parcels:
            p_node, d_node = req.pickup_node, req.dropoff_node
            for t_idx, route in enumerate(self.routes):
                n = len(route.stops)
                # Vòng lặp lồng i, j để thử mọi cặp vị trí (lấy hàng, giao hàng) với i <= j
                # -> đây là phần khiến độ phức tạp cao hơn hành khách (chỉ có 1 vòng i)
                for i in range(n + 1):
                    for j in range(i, n + 1):
                        # Chèn Pickup tại i và Dropoff tại j (sau khi đã chèn i, mảng dịch phải 1 vị trí
                        # từ i trở đi, nên dùng route.stops[i:j] để lấy đúng đoạn giữa 2 điểm chèn)
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