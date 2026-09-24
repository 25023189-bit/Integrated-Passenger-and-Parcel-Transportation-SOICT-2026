import math
from typing import List, Optional, Tuple
from models import ProblemInstance, Route, PassengerRequest, ParcelRequest, Node
from validator import is_route_valid
from utils import calculate_next_time, calculate_next_load

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