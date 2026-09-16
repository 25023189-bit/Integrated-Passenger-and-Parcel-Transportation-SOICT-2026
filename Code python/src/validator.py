from models import Route, ProblemInstance
import math

def validate_temporal_flow(route: Route, instance: ProblemInstance) -> bool:
    """
    Kiểm tra bảo toàn luồng thời gian cho toàn bộ danh sách điểm dừng của Taxi k.
    """
    stops = route.stops
    if not stops:
        return True  # Lộ trình rỗng luôn hợp lệ về mặt thời gian
    
    # [Khởi tạo luồng]: Xe xuất phát từ Depot Ok tại thời điểm dep_0 = 0.0
    dep_u = 0.0 
    u_idx = route.taxi.depot_node.matrix_index  # Lấy chỉ số ma trận của nút Depot xuất phát
    
    # Tối ưu Local Binding: Gán ma trận vào biến cục bộ để tránh Dot Lookup overhead trong Python
    time_matrix = instance.time_matrix 
    
    for node in stops:
        v_idx = node.matrix_index
        
        # Trích xuất khung thời gian (E_v, L_v) và thời gian dịch vụ S_v từ thuộc tính của Node/Request
        early_v, late_v, service_v = instance.get_node_time_windows(node)
        
        # [Công thức 2]: arr_v = dep_u + t(u, v)
        arr_v = dep_u + time_matrix[u_idx][v_idx]
        
        # [Kiểm tra vi phạm khung thời gian đón/giao] (Công thức 1, 6, 7 trong đề)
        if arr_v > late_v:
            return False  # Phát hiện vi phạm -> Loại bỏ lời giải ngay lập tức (Tối ưu TLE)
            
        # [Công thức 3]: srv_v = max(arr_v, E_v)
        srv_v = arr_v if arr_v >= early_v else early_v
        
        # [Công thức 4]: Cập nhật dep_u cho điểm tiếp theo: dep_v = srv_v + S_v
        dep_u = srv_v + service_v
        u_idx = v_idx  # Điểm v trở thành điểm u cho bước lặp tiếp theo
        
    return True  # Tất cả các nút đều thỏa mãn luồng thời gian

def validate_spatial_flow(route: Route, instance: ProblemInstance) -> bool:
    """
    Kiểm tra tính liên tục luồng không gian (Spatial Flow Conservation - Công thức 1).
    Đảm bảo xe bắt đầu từ Depot Ok, di chuyển liên tục qua từng nút trung gian u 
    (In-degree = Out-degree = 1) và không bị gãy chuỗi lộ trình.
    """
    stops = route.stops
    if not stops:
        return True  # Xe không phục vụ đơn nào vẫn hợp lệ về mặt luồng không gian

    # 1. Khai báo biến cục bộ để tránh overhead truy xuất thuộc tính (Dot Lookup Optimization)
    cost_matrix = instance.cost_matrix
    time_matrix = instance.time_matrix
    num_nodes = len(cost_matrix)

    # 2. [Kiểm tra điểm xuất phát v_0^k = O_k]: Luồng đi ra đầu tiên phải bắt nguồn từ Depot của đúng Taxi k
    depot_node = route.taxi.depot_node
    first_node = stops[0]
    
    u_idx = depot_node.matrix_index
    v_idx = first_node.matrix_index

    # Lý do: Đảm bảo index nằm trong kích thước ma trận 2N + 2M + K
    if not (0 <= u_idx < num_nodes and 0 <= v_idx < num_nodes):
        return False

    # Lý do: Kiểm tra kết nối từ Depot đến điểm ghé thăm đầu tiên có tồn tại hay không
    if math.isinf(cost_matrix[u_idx][v_idx]) or math.isinf(time_matrix[u_idx][v_idx]):
        return False

    # 3. [Bảo toàn luồng trung gian (Công thức 1)]: Sum(x_u,j) - Sum(x_i,u) = 0
    # Trong biểu diễn mảng liên kết (List[Node]), mỗi nút u ở vị trí i tự động có 
    # 1 cung vào từ (i-1) và 1 cung ra tới (i+1). Ta kiểm tra tính liên tục của tất cả các cung di chuyển này.
    for i in range(len(stops) - 1):
        curr_idx = stops[i].matrix_index
        next_idx = stops[i + 1].matrix_index

        # Kiểm tra giới hạn chỉ số ma trận
        if not (0 <= curr_idx < num_nodes and 0 <= next_idx < num_nodes):
            return False

        # [Tối ưu TLE]: Trả về False ngay lập tức nếu cung di chuyển giữa 2 nút trung gian bị gãy (Cost = inf)
        if math.isinf(cost_matrix[curr_idx][next_idx]) or math.isinf(time_matrix[curr_idx][next_idx]):
            return False

    return True  # Chuỗi lộ trình hoàn toàn liên tục và bảo toàn luồng không gian

def validate_capacity_flow(route: Route, instance: ProblemInstance) -> bool:
    """
    Kiểm tra Bảo toàn Luồng Tải trọng (Capacity Flow Conservation - Công thức 5 & 6).
    Đảm bảo tải trọng trên xe tại mọi thời điểm thỏa mãn 0 <= load_v <= Q_k.
    """
    stops = route.stops
    if not stops:
        return True  # Lộ trình không chở bưu kiện nào luôn hợp lệ về tải trọng

    # 1. Tối ưu Local Variable Binding: Gán biến local để tăng tốc độ truy cập thuộc tính Python
    capacity = route.taxi.capacity
    current_load = 0.0  # Ban đầu taxi xuất phát từ Depot với xe rỗng (load = 0)

    # 2. Duyệt qua từng điểm dừng trong chuỗi lộ trình R_k
    for node in stops:
        # Lý do: Chỉ cập nhật tải trọng khi nút là dịch vụ Bưu kiện (PARCEL)
        if node.type == 'PARCEL_PICKUP':
            # Tra cứu thông tin yêu cầu bưu kiện j
            parcel = instance.get_parcel_by_node(node)
            if parcel is None:
                return False
            
            # [Công thức 5]: load_v = load_u + w_j
            current_load += parcel.weight
            
            # [Công thức 6 - Tối ưu TLE]: Ngắt sớm ngay khi tải trọng vượt quá sức chứa taxi Q_k
            if current_load > capacity:
                return False

        elif node.type == 'PARCEL_DROPOFF':
            parcel = instance.get_parcel_by_node(node)
            if parcel is None:
                return False
            
            # [Công thức 5]: load_v = load_u - w_j
            current_load -= parcel.weight
            
            # [Công thức 6]: Tải trọng không được âm (tránh trường hợp giao hàng chưa lấy)
            if current_load < -1e-7:
                return False

    # 3. Kiểm tra Bảo toàn Luồng cuối chuyến: Sau khi chạy hết tuyến, xe phải trả sạch hàng (load về 0)
    if current_load > 1e-7:
        return False  # Vẫn còn bưu kiện dư trên xe chưa giao

    return True  # Toàn bộ lộ trình hoàn toàn bảo toàn luồng tải trọng

def validate_direct_passenger_flow(route: Route, instance: ProblemInstance) -> bool:
    """
    Kiểm tra Bảo toàn Luồng Trực tiếp Hành khách (Công thức 7).
    Đảm bảo: Nếu v_r^k = P_i^n thì v_{r+1}^k = D_i^n (Nút ngay sau điểm đón BẮT BUỘC là điểm trả của khách đó).
    """
    stops = route.stops
    if not stops:
        return True  # Xe không chở khách nào thì luôn hợp lệ

    n_stops = len(stops)

    for i, node in enumerate(stops):
        # 1. Phát hiện nút Đón khách (PASSENGER_PICKUP)
        if node.type == 'PASSENGER_PICKUP':
            # Tra cứu thông tin yêu cầu hành khách i
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None:
                return False
            
            # [Công thức 7]: Nút liền sau (i + 1) BẮT BUỘC phải tồn tại và đúng là điểm trả D_i^n
            if i + 1 >= n_stops:
                return False 
                
            next_node = stops[i + 1]
            
            # Lý do so sánh node.id: Đảm bảo v_{r+1}^k = D_i^n (Điểm trả khớp đúng ID với điểm đón)
            if next_node.id != passenger_req.dropoff_node.id:
                return False  # Vi phạm luồng chở khách trực tiếp (có nút khác chen vào giữa)

        # 2. Kiểm tra chiều ngược lại đối với nút Trả khách (PASSENGER_DROPOFF)
        elif node.type == 'PASSENGER_DROPOFF':
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None:
                return False
            
            # Điểm trả khách không thể nằm ở đầu danh sách stops (thiếu điểm đón P_i^n)
            if i == 0:
                return False
                
            prev_node = stops[i - 1]
            
            # Lý do so sánh với prev_node: Đảm bảo nút ngay trước D_i^n phải là P_i^n của cùng một khách
            if prev_node.id != passenger_req.pickup_node.id:
                return False  # Vi phạm luồng đón trước - trả sau kề nhau

    return True  # Lộ trình thỏa mãn tuyệt đối luồng chở khách trực tiếp

def validate_time_windows_and_precedence(route: Route, instance: ProblemInstance) -> bool:
    """
    Kiểm tra Ràng buộc Khung thời gian (Time Windows) và Thứ tự Nhận trước - Giao sau của Bưu kiện.
    """
    stops = route.stops
    if not stops:
        return True

    current_time = 0.0
    current_node = route.taxi.depot_node
    
    # Tập hợp theo dõi các bưu kiện đã lấy hàng trên lộ trình này
    picked_up_parcels = set()

    for node in stops:
        # 1. Tính thời gian di chuyển t(u, v) từ nút trước đó
        travel_time = instance.time_matrix[current_node.matrix_index][node.matrix_index]
        arrival_time = current_time + travel_time

        # 2. Kiểm tra Ràng buộc Khung thời gian và Thứ tự ưu tiên
        if node.type == 'PASSENGER_PICKUP':
            req = instance.get_passenger_by_node(node)
            if req is None or arrival_time > req.late_pickup:  # arrP <= L_i^n
                return False
            start_service = max(arrival_time, req.early_pickup)
            departure_time = start_service + req.service_time

        elif node.type == 'PASSENGER_DROPOFF':
            req = instance.get_passenger_by_node(node)
            if req is None:
                return False
            # Xe đến trả khách ngay sau khi đi trực tiếp
            start_service = arrival_time
            departure_time = start_service + req.service_time

        elif node.type == 'PARCEL_PICKUP':
            req = instance.get_parcel_by_node(node)
            if req is None or arrival_time > req.late_pickup:  # arrP <= L_j^{h,p}
                return False
            start_service = max(arrival_time, req.early_pickup)
            departure_time = start_service + req.service_time
            
            # Ghi nhận bưu kiện đã được lấy hàng
            picked_up_parcels.add(req.id)

        elif node.type == 'PARCEL_DROPOFF':
            req = instance.get_parcel_by_node(node)
            if req is None:
                return False
            
            # [Ràng buộc Nhận trước - Giao sau]: Phải lấy hàng rồi mới được giao
            if req.id not in picked_up_parcels:
                return False

            if arrival_time > req.late_dropoff:  # arrD <= L_j^{h,d}
                return False
            start_service = max(arrival_time, req.early_dropoff)
            departure_time = start_service + req.service_time
            
            # Đã giao xong bưu kiện
            picked_up_parcels.remove(req.id)

        # Cập nhật mốc thời gian và vị trí hiện tại
        current_time = departure_time
        current_node = node

    return True

def is_route_valid(route: Route, instance: ProblemInstance) -> bool:
    """
    Hàm tổng hợp kiểm tra toàn bộ Ràng buộc Cứng (Hard Constraints) cho 1 Lộ trình.
    """
    return (
        validate_spatial_flow(route, instance) and
        validate_capacity_flow(route, instance) and
        validate_direct_passenger_flow(route, instance) and
        validate_time_windows_and_precedence(route, instance)
    )