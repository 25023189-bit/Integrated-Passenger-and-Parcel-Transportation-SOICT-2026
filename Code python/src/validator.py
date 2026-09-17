from models import Route, ProblemInstance
import math

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