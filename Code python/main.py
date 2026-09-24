import time
import random
import math

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src'))

from models import Node, PassengerRequest, ParcelRequest, Taxi, Route, ProblemInstance
from utils import calculate_next_time, get_spatial_transition, calculate_next_load
from validator import (
    is_route_valid,
    validate_spatial_flow,
    validate_temporal_flow,
    validate_capacity_flow,
    validate_direct_passenger_flow,
)
from greedy_solver import GreedySolver, calculate_objective_value
from random_solver import RandomSolver
from hill_climbing import HillClimbingSolver
from evaluator import calculate_delta_cost, calculate_delta_time, check_capacity_delta


# 1: Sinh dữ liệu mẫu nhỏ

def generate_demo_instance() -> ProblemInstance:
    """
    Sinh 1 test case NHỎ (2 hành khách, 2 bưu kiện, 2 xe) với tọa độ
    tường minh, để có thể tự tính tay và so sánh với kết quả của code
    Quy ước: cost = khoảng cách Euclid, time = cost / 2.0 )
    """

    # (id_node, type, (x, y))
    coords = [
        (0, 'DEPOT',             (0, 0)),
        (1, 'PASSENGER_PICKUP',  (2, 0)),   # Khách A đón
        (2, 'PASSENGER_DROPOFF', (2, 3)),   # Khách A trả
        (3, 'PASSENGER_PICKUP',  (4, 0)),   # Khách B đón
        (4, 'PASSENGER_DROPOFF', (4, 2)),   # Khách B trả
        (5, 'PARCEL_PICKUP',     (1, 1)),   # Hàng C lấy
        (6, 'PARCEL_DROPOFF',    (5, 1)),   # Hàng C giao
        (7, 'PARCEL_PICKUP',     (3, 3)),   # Hàng D lấy
        (8, 'PARCEL_DROPOFF',    (0, 4)),   # Hàng D giao
    ]

    # Tạo danh sách đối tượng Node từ coords (mỗi Node ứng với 1 dòng trong ma trận)
    nodes = [Node(id=i, type=t, matrix_index=i) for i, t, _ in coords]

    # Tách riêng phần tọa độ (x, y) ra để tính khoảng cách
    xy = [c for _, _, c in coords]

    n = len(nodes)

    # Khởi tạo ma trận chi phí và ma trận thời gian toàn số 0, kích thước n x n
    cost_matrix = [[0.0] * n for _ in range(n)]
    time_matrix = [[0.0] * n for _ in range(n)]
    for r in range(n):
        for c in range(n):
            if r != c:  # Không tính khoảng cách từ 1 node đến chính nó (giữ = 0)
                dx = xy[r][0] - xy[c][0]
                dy = xy[r][1] - xy[c][1]

                # Khoảng cách Euclid giữa 2 điểm, làm tròn 2 chữ số thập phân
                dist = round(math.hypot(dx, dy), 2)
                cost_matrix[r][c] = dist                  # Chi phí = khoảng cách
                time_matrix[r][c] = round(dist / 2.0, 2)  # Thời gian = chi phí / tốc độ (2 đơn vị/thời gian)
 
    # Khai báo 2 yêu cầu Hành khách, mỗi yêu cầu gắn với 1 cặp node (pickup, dropoff)
    passengers = [
        PassengerRequest(
            id=1, pickup_node=nodes[1], dropoff_node=nodes[2],
            revenue=100.0,        # Doanh thu nếu phục vụ được khách A
            early_pickup=0.0,     # Sớm nhất có thể đón lúc t=0
            late_pickup=50.0,     # Muộn nhất phải đón trước t=50, quá thì vi phạm
            service_time=1.0      # Thời gian phục vụ tại mỗi điểm đón/trả
        ),
        PassengerRequest(
            id=2, pickup_node=nodes[3], dropoff_node=nodes[4],
            revenue=80.0, early_pickup=0.0, late_pickup=50.0, service_time=1.0
        ),
    ]

    # Khai báo 2 yêu cầu Bưu kiện, có thêm early/late cho cả pickup lẫn dropoff và trọng lượng (weight)
    parcels = [
        ParcelRequest(
            id=1, pickup_node=nodes[5], dropoff_node=nodes[6],
            revenue=60.0, weight=3.0,   # Hàng C nặng 3kg
            early_pickup=0.0, late_pickup=50.0,
            early_dropoff=0.0, late_dropoff=50.0, service_time=1.0
        ),
        ParcelRequest(
            id=2, pickup_node=nodes[7], dropoff_node=nodes[8],
            revenue=40.0, weight=2.0,   # Hàng D nặng 2kg
            early_pickup=0.0, late_pickup=50.0,
            early_dropoff=0.0, late_dropoff=50.0, service_time=1.0
        ),
    ]

    # Khai báo 2 xe taxi, cùng xuất phát từ Depot (nodes[0]), sức chứa bưu kiện tối đa = 5
    taxis = [
        Taxi(id=1, depot_node=nodes[0], capacity=5.0),
        Taxi(id=2, depot_node=nodes[0], capacity=5.0),
    ]
 
    # Gói toàn bộ dữ liệu (xe, khách, hàng, 2 ma trận) vào 1 đối tượng ProblemInstance
    return ProblemInstance(
        taxis=taxis, passengers=passengers, parcels=parcels,
        time_matrix=time_matrix, cost_matrix=cost_matrix
    )

def print_node_table(instance: ProblemInstance):
    """In ra bảng liệt kê toàn bộ node đang có trong instance, để dễ đối chiếu id <-> loại node."""
    print("Bảng các Node trong dữ liệu demo:")
    print(f"{'id':>3} {'type':<18} {'matrix_index':>12}")
 
    # Gom tất cả node lại thành 1 danh sách: depot + (pickup, dropoff) của từng khách/hàng
    all_nodes = [instance.taxis[0].depot_node]
    for p in instance.passengers:
        all_nodes += [p.pickup_node, p.dropoff_node]
    for h in instance.parcels:
        all_nodes += [h.pickup_node, h.dropoff_node]
 
    # In từng dòng: id node, loại node, chỉ số trong ma trận (matrix_index)
    for node in all_nodes:
        print(f"{node.id:>3} {node.type:<18} {node.matrix_index:>12}")

# 2: Test utils.py

def demo_utils(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO utils.py")
    print("-" * 60)

    # --- get_spatial_transition: tra cứu (cost, time) giữa 2 node ---
    u_idx, v_idx = 0, 1  # Depot -> Điểm đón khách A
    cost, t = get_spatial_transition(u_idx, v_idx, instance.cost_matrix, instance.time_matrix)
    print(f"get_spatial_transition(Depot -> P_A): cost={cost}, time={t}")

    # --- calculate_next_time: tính mốc thời gian đến/phục vụ/rời điểm P_A ---
    early_v, late_v, service_v = instance.get_node_time_windows(instance.passengers[0].pickup_node)
    result = calculate_next_time(
        dep_u=0.0, u_idx=u_idx, v_idx=v_idx, time_matrix=instance.time_matrix,
        early_v=early_v, late_v=late_v, service_v=service_v
    )
    if result:
        arr_v, srv_v, dep_v = result
        print(f"calculate_next_time(Depot -> P_A): arrival={arr_v}, start_service={srv_v}, departure={dep_v}")
    else:
        print("calculate_next_time: đến muộn hơn late_pickup -> vi phạm (trả về None)")

    # --- calculate_next_load: cộng tải khi lấy bưu kiện C (weight=3) trên xe capacity=5 ---
    new_load = calculate_next_load(
        current_load=0.0, node_type='PARCEL_PICKUP',
        weight=instance.parcels[0].weight, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (lấy hàng C, weight=3, capacity=5): load mới = {new_load}")

    # --- thử lấy thêm hàng D (weight=2) -> tổng 5, vẫn vừa đủ ---
    new_load_2 = calculate_next_load(
        current_load=new_load, node_type='PARCEL_PICKUP',
        weight=instance.parcels[1].weight, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (lấy thêm hàng D, weight=2): load mới = {new_load_2}")

    # --- thử vi phạm: lấy thêm 1kg nữa (giả lập) sẽ vượt capacity=5 -> trả về None ---
    overload = calculate_next_load(
        current_load=new_load_2, node_type='PARCEL_PICKUP',
        weight=1.0, capacity=instance.taxis[0].capacity
    )
    print(f"calculate_next_load (thử lấy thêm 1kg khi đã đầy 5/5): kết quả = {overload}  (None nghĩa là vi phạm)")


# 3: Test validator.py trên 1 lộ trình hợp lệ và 1 lộ trình không hợp lệ

def demo_validator(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO validator.py")
    print("-" * 60)

    taxi = instance.taxis[0]
    p_a = instance.passengers[0]   # nodes 1, 2
    h_c = instance.parcels[0]      # nodes 5, 6

    # Lộ trình hợp lệ: đón/trả khách A liền kề, rồi lấy/giao hàng C 
    good_route = Route(taxi=taxi, stops=[
        p_a.pickup_node, p_a.dropoff_node, h_c.pickup_node, h_c.dropoff_node
    ])
    print("Lộ trình hợp lệ: Depot -> P_A -> D_A -> P_C -> D_C")
    print(f"  validate_spatial_flow          = {validate_spatial_flow(good_route, instance)}")
    print(f"  validate_temporal_flow         = {validate_temporal_flow(good_route, instance)}")
    print(f"  validate_capacity_flow         = {validate_capacity_flow(good_route, instance)}")
    print(f"  validate_direct_passenger_flow = {validate_direct_passenger_flow(good_route, instance)}")
    print(f"  is_route_valid (gộp cả 4)      = {is_route_valid(good_route, instance)}")

    # Lộ trình vi phạm: chèn 1 điểm khác xen giữa đón/trả khách A (phá vỡ Công thức 7)
    bad_route = Route(taxi=taxi, stops=[
        p_a.pickup_node, h_c.pickup_node, p_a.dropoff_node, h_c.dropoff_node
    ])
    print("\nLộ trình VI PHẠM: Depot -> P_A -> P_C -> D_A -> D_C  (ghé P_C xen giữa đón/trả khách A)")
    print(f"  validate_direct_passenger_flow = {validate_direct_passenger_flow(bad_route, instance)}  (False = đúng như kỳ vọng)")
    print(f"  is_route_valid (gộp cả 4)      = {is_route_valid(bad_route, instance)}")

    # --- Lộ trình vi phạm tải trọng: giả lập taxi sức chứa nhỏ ---
    small_taxi = Taxi(id=99, depot_node=taxi.depot_node, capacity=2.0)  # nhỏ hơn weight hàng C=3
    overload_route = Route(taxi=small_taxi, stops=[h_c.pickup_node, h_c.dropoff_node])
    print("\nLộ trình VI PHẠM tải trọng: xe capacity=2 nhưng hàng C nặng 3")
    print(f"  validate_capacity_flow = {validate_capacity_flow(overload_route, instance)}  (False = đúng như kỳ vọng)")


# 4: Test greedy_solver.py xem từng bước chèn

def demo_greedy_solver(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO greedy_solver.py")
    print("-" * 60)

    solver = GreedySolver(instance)

    # Gọi trực tiếp 2 hàm tìm-vị-trí-chèn-tốt-nhất TRƯỚC khi solve(),
    # để xem thuật toán "nhìn thấy" gì ở bước đầu tiên.
    pass_req, p_taxi, p_pos, p_gain = solver.find_best_passenger_insertion()
    print(f"Bước đầu - chèn khách tốt nhất: request={pass_req.id if pass_req else None}, "
          f"taxi_idx={p_taxi}, vị trí={p_pos}, gain={p_gain:.2f}")

    parcel_req, r_taxi, r_i, r_j, r_gain = solver.find_best_parcel_insertion()
    print(f"Bước đầu - chèn hàng tốt nhất:  request={parcel_req.id if parcel_req else None}, "
          f"taxi_idx={r_taxi}, vị trí lấy={r_i}, vị trí giao={r_j}, gain={r_gain:.2f}")

    # Chạy toàn bộ vòng lặp solve()
    routes = solver.solve()

    print("\nKết quả cuối cùng của GreedySolver:")
    for route in routes:
        stop_ids = [s.id for s in route.stops]
        print(f"  Taxi {route.taxi.id}: Depot -> {stop_ids}")

    obj = calculate_objective_value(routes, instance)
    print(f"\nTổng lợi nhuận (Greedy) = {obj:.2f}")
    return routes, obj



# 5: Test random_solver.py để so sánh

def demo_random_solver(instance: ProblemInstance):
    print("\n" + "-" * 60)
    print("DEMO random_solver.py")
    print("-" * 60)

    solver = RandomSolver(instance, seed=1)
    routes = solver.solve()

    print("Kết quả của RandomSolver:")
    for route in routes:
        stop_ids = [s.id for s in route.stops]
        print(f"  Taxi {route.taxi.id}: Depot -> {stop_ids}")

    obj = calculate_objective_value(routes, instance)
    print(f"\nTổng lợi nhuận (Random) = {obj:.2f}")
    return routes, obj

# 5b: Test hill_climbing.py (dùng _mock_relocate_operator, chưa có operators.py của Hà Thu)

def demo_hill_climbing(instance: ProblemInstance):
    """
    Chạy HillClimbingSolver trên nền lời giải cơ sở của GreedySolver, dùng
    _mock_relocate_operator (ngẫu nhiên) làm toán tử sinh hàng xóm tạm thời,
    vì operators.py (relocate/swap thật) của Hà Thu chưa có.
    Mục đích: kiểm chứng vòng lặp Hill Climbing + evaluator.py không crash,
    và benefit sau khi chạy không bao giờ TỆ HƠN benefit trước khi chạy
    (vì thuật toán chỉ accept khi delta_benefit > 0).
    """
    print("\n" + "-" * 60)
    print("DEMO hill_climbing.py")
    print("-" * 60)

    # 1. Lấy lời giải cơ sở từ GreedySolver làm điểm khởi đầu
    greedy_solver = GreedySolver(instance)
    greedy_routes = greedy_solver.solve()
    benefit_before = calculate_objective_value(greedy_routes, instance)

    print("Lộ trình TRƯỚC Hill Climbing (từ Greedy):")
    for route in greedy_routes:
        print(f"  Taxi {route.taxi.id}: Depot -> {[s.id for s in route.stops]}")
    print(f"Benefit TRƯỚC = {benefit_before:.2f}")

    # 2. HillClimbingSolver nhận vào List[List[Node]], không phải List[Route],
    #    nên phải tách .stops ra trước khi truyền vào.
    initial_routes = [route.stops for route in greedy_routes]

    random.seed(7)  # cố định seed để chạy lại tái lập được kết quả khi debug
    hc_solver = HillClimbingSolver(instance, initial_routes)
    final_stops_list = hc_solver.solve()

    # 3. Đóng gói lại thành Route (giữ nguyên taxi tương ứng theo thứ tự) để
    #    tính lại benefit bằng đúng hàm calculate_objective_value dùng chung.
    from models import Route
    final_routes = [
        Route(taxi=greedy_routes[i].taxi, stops=final_stops_list[i])
        for i in range(len(greedy_routes))
    ]
    benefit_after = calculate_objective_value(final_routes, instance)

    print("\nLộ trình SAU Hill Climbing:")
    for route in final_routes:
        print(f"  Taxi {route.taxi.id}: Depot -> {[s.id for s in route.stops]}")
    print(f"Benefit SAU  = {benefit_after:.2f}")

    # 4. Cảnh báo tự động nếu benefit bị TỆ HƠN sau khi "tối ưu" -> có nghĩa là
    #    evaluator.py hoặc vòng lặp accept/reject đang có bug logic.
    if benefit_after < benefit_before - 1e-6:
        print("[CẢNH BÁO] Benefit SAU < Benefit TRƯỚC -> có bug trong logic accept của Hill Climbing!")
    else:
        print("Benefit không giảm sau Hill Climbing -> logic accept/reject ổn (dùng mock operator).")

    return final_routes, benefit_after


# 5c: Test riêng evaluator.py (calculate_delta_cost / check_capacity_delta),
#     đặc biệt case bưu kiện TÁCH RỜI (pickup và dropoff không nằm liền kề nhau)

def demo_evaluator(instance: ProblemInstance):
    """
    calculate_delta_cost() trong evaluator.py chỉ tính delta cho việc chèn
    ĐÚNG 1 node giữa 2 node A, B. Với bưu kiện tách rời (pickup ở vị trí i,
    dropoff ở vị trí j > i, có thể có các điểm khác chen giữa), phải gọi
    hàm này 2 LẦN riêng biệt (1 lần cho điểm chèn pickup, 1 lần cho điểm
    chèn dropoff) rồi CỘNG LẠI - giống đúng cách get_parcel_delta_cost()
    trong greedy_solver.py làm ở nhánh i != j.

    Test này dựng 1 route có sẵn, chèn 1 bưu kiện mới TÁCH RỜI vào, rồi so
    delta_cost tính bằng evaluator.calculate_delta_cost (gọi 2 lần, cộng
    lại) với cách tính "từ đầu" (get_route_cost kiểu greedy_solver) để chắc
    2 cách cho cùng kết quả.
    """
    print("\n" + "-" * 60)
    print("DEMO evaluator.py - case bưu kiện tách rời")
    print("-" * 60)

    cost_mat = instance.cost_matrix
    taxi = instance.taxis[0]

    # Route có sẵn (đã hợp lệ, không tính đơn mới): P_A -> D_A -> P_C -> D_C
    p_a, h_c = instance.passengers[0], instance.parcels[0]
    stops = [p_a.pickup_node, p_a.dropoff_node, h_c.pickup_node, h_c.dropoff_node]

    def route_cost(depot, stop_list):
        if not stop_list:
            return 0.0
        c = cost_mat[depot.matrix_index][stop_list[0].matrix_index]
        for k in range(len(stop_list) - 1):
            c += cost_mat[stop_list[k].matrix_index][stop_list[k + 1].matrix_index]
        return c

    old_cost = route_cost(taxi.depot_node, stops)

    # Bưu kiện thứ 2 (parcel[1], node 7-8) sẽ được chèn TÁCH RỜI:
    # pickup vào vị trí i=1 (giữa D_A và P_C), dropoff vào vị trí j=3
    # (giữa D_C và cuối route) -> có 2 điểm dừng khác (P_C, D_C) nằm
    # giữa pickup và dropoff của bưu kiện mới, đúng nghĩa "tách rời".
    h_d = instance.parcels[1]
    i, j = 1, 3
    new_stops = stops[:i] + [h_d.pickup_node] + stops[i:j] + [h_d.dropoff_node] + stops[j:]
    new_cost_bruteforce = route_cost(taxi.depot_node, new_stops)
    delta_cost_bruteforce = new_cost_bruteforce - old_cost

    # --- Cách tính bằng evaluator.calculate_delta_cost, gọi 2 lần rồi cộng ---
    # Điểm chèn pickup: A = node liền trước vị trí i (ở mảng CŨ), B = node đang ở vị trí i
    A1 = stops[i - 1] if i > 0 else taxi.depot_node
    B1 = stops[i]
    delta_pickup = calculate_delta_cost(A1, B1, h_d.pickup_node, cost_mat)

    # Điểm chèn dropoff: C = node liền trước vị trí j (ở mảng CŨ), D_next = node đang ở vị trí j
    C1 = stops[j - 1]
    D_next1 = stops[j] if j < len(stops) else None
    if D_next1 is not None:
        delta_dropoff = calculate_delta_cost(C1, D_next1, h_d.dropoff_node, cost_mat)
    else:
        # Chèn ở cuối route -> không có cạnh (C, D_next) để "xóa", chỉ có cạnh (C, dropoff) mới
        delta_dropoff = cost_mat[C1.matrix_index][h_d.dropoff_node.matrix_index]

    delta_cost_evaluator = delta_pickup + delta_dropoff

    print(f"Route cũ: Depot -> {[s.id for s in stops]}  (cost = {old_cost:.2f})")
    print(f"Chèn tách rời bưu kiện D: pickup tại vị trí {i}, dropoff tại vị trí {j}")
    print(f"Route mới: Depot -> {[s.id for s in new_stops]}  (cost = {new_cost_bruteforce:.2f})")
    print(f"Delta cost (tính lại từ đầu)         = {delta_cost_bruteforce:.4f}")
    print(f"Delta cost (evaluator, gọi 2 lần)    = {delta_cost_evaluator:.4f}")
    match = abs(delta_cost_bruteforce - delta_cost_evaluator) < 1e-6
    print(f"=> {'KHỚP' if match else 'LỆCH -> CÓ BUG!'}")

    # --- Test check_capacity_delta với case tách rời: phát hiện hạn chế của hàm ---
    # check_capacity_delta CHỈ nhận 1 insert_idx (điểm pickup), KHÔNG có tham số
    # nào cho biết dropoff nằm ở đâu -> nó cộng "weight" vào TOÀN BỘ các điểm dừng
    # từ insert_idx đến HẾT route, coi như bưu kiện không bao giờ được giao (tệ nhất).
    # Với bưu kiện tách rời (dropoff nằm giữa route, không phải cuối), cách tính này
    # có thể từ chối 1 phương án chèn HOÀN TOÀN HỢP LỆ, chỉ vì tải trọng CŨ (không
    # liên quan gì đến bưu kiện mới) ở phía sau điểm dropoff vốn đã cao sẵn.
    print("\n--- Test check_capacity_delta với case tách rời (phát hiện hạn chế) ---")
    capacity = 4.0  # cố ý đặt thấp hơn h_c.weight(3) + h_d.weight(2) = 5, để lộ rõ hạn chế
    # current_loads mô phỏng: tải trọng CŨ (trước khi chèn) sau mỗi điểm dừng của route gốc
    # (route gốc gồm 4 stop: P_A, D_A, P_C, D_C -> không có bưu kiện nào trên xe ở 2 stop đầu,
    # có bưu kiện h_c (weight=3) từ stop index2 (P_C) đến hết vì D_C là stop cuối)
    current_loads = [0.0, 0.0, h_c.weight, 0.0]  # load sau mỗi stop: [P_A, D_A, P_C, D_C]

    # Giả sử bưu kiện D (weight=2) được chèn pickup ở vị trí i=1, và dropoff ngay
    # sau đó ở vị trí 2 (TRƯỚC khi chạm P_C) -> cửa sổ mang hàng D rất ngắn, không
    # hề chồng với lúc xe đang chở hàng C (index2-3) -> phải HỢP LỆ.
    is_valid = check_capacity_delta(
        route_stops=stops, insert_idx=1, insert_node=h_d.pickup_node,
        capacity=capacity, current_loads=current_loads, weight=h_d.weight
    )
    print(f"Chèn pickup D (weight={h_d.weight}) tại vị trí 1, dropoff ngay sau (không chạm hàng C):")
    print(f"  check_capacity_delta trả về = {is_valid}")
    print(f"  (Load thực tế tại các vị trí sau đó: index2 có h_c.weight={h_c.weight} sẵn trên xe,")
    print(f"   nếu hàm cộng thêm weight={h_d.weight} vào TẤT CẢ vị trí phía sau (kể cả sau khi D đã")
    print(f"   được giao) thì {h_c.weight}+{h_d.weight}={h_c.weight + h_d.weight} so với capacity={capacity}"
          f" -> {'VƯỢT' if h_c.weight + h_d.weight > capacity else 'không vượt'})")
    if not is_valid and h_c.weight + h_d.weight > capacity:
        print("  => XÁC NHẬN HẠN CHẾ: hàm từ chối phương án này dù nó hợp lệ trong thực tế,")
        print("     vì không biết bưu kiện D đã được giao (dropoff) TRƯỚC khi xe chạm hàng C.")
        print("     Cần thêm tham số 'dropoff_idx' để hàm chỉ cộng weight trong đúng khoảng")
        print("     [insert_idx, dropoff_idx), không cộng tới hết route.")


# 5d: Test riêng calculate_delta_time() bằng số liệu TỰ TAY dựng (không phụ thuộc
#     dữ liệu demo ngẫu nhiên), để có thể dò lại từng bước bằng tay/máy tính.

def demo_evaluator_delta_time():
    """
    Dựng 1 mini ProblemInstance CHỈ để test calculate_delta_time():
      - 1 depot O (matrix_index 0)
      - node A (matrix_index 1): parcel pickup của bưu kiện P1, window [0, 100]
      - node B (matrix_index 2): parcel dropoff của bưu kiện P1, window [0, 100]
      - node X (matrix_index 3): parcel pickup của bưu kiện P2 - node sẽ được CHÈN
        giữa A và B, window [0, 20] hoặc [0, 6] tùy case test

    Ma trận thời gian t(u, v) tự chọn (không đối xứng, đúng tinh thần đề bài):
        t(O,A)=5   t(O,B)=10  t(O,X)=7
        t(A,B)=4   t(A,X)=3
        t(B,X)=6

    ---- Case 1: X có window rộng [0, 20] -> chèn hợp lệ ----
    Tính TAY (theo đúng công thức 2,3,4 trong đề bài):
      dep_A (route CŨ, Depot->A->B): arr_A = 0 + t(O,A) = 5
                                      srv_A = max(5, E_A=0) = 5 ; dep_A = 5 + S_A(0) = 5
      old_dep_B (route CŨ): arr_B = dep_A + t(A,B) = 5 + 4 = 9
                             srv_B = max(9, 0) = 9 ; old_dep_B = 9 + 0 = 9

      Chèn X giữa A và B (route MỚI: Depot->A->X->B):
      arr_X = dep_A + t(A,X) = 5 + 3 = 8   (<= late_X=20, HỢP LỆ)
      srv_X = max(8, E_X=0) = 8 ; dep_X = 8 + S_X(2) = 10
      arr_B_new = dep_X + t(X,B) = 10 + 6 = 16   (<= late_B=100, HỢP LỆ)
      srv_B_new = max(16, 0) = 16 ; dep_B_new = 16 + 0 = 16

      => delta_time (TAY) = dep_B_new - old_dep_B = 16 - 9 = 7

    ---- Case 2: X có window hẹp [0, 6] -> arr_X = 8 > late_X = 6 -> PHẢI trả về None ----
    """
    print("\n" + "-" * 60)
    print("DEMO evaluator.py - test calculate_delta_time() bằng số liệu tay")
    print("-" * 60)

    depot = Node(id=0, type='DEPOT', matrix_index=0)
    node_A = Node(id=1, type='PARCEL_PICKUP', matrix_index=1)
    node_B = Node(id=2, type='PARCEL_DROPOFF', matrix_index=2)
    node_X = Node(id=3, type='PARCEL_PICKUP', matrix_index=3)

    parcel_1 = ParcelRequest(
        id=1, pickup_node=node_A, dropoff_node=node_B, revenue=0.0,
        early_pickup=0.0, late_pickup=100.0,
        early_dropoff=0.0, late_dropoff=100.0,
        service_time=0.0, weight=0.0,
    )

    INF = float('inf')
    #        O    A    B    X
    time_matrix = [
        [0.0, 5.0, 10.0, 7.0],   # từ O
        [5.0, 0.0, 4.0, 3.0],    # từ A  (t(A,B)=4, t(A,X)=3)
        [10.0, 4.0, 0.0, 6.0],   # từ B  (t(B,X)=6, và QUAN TRỌNG: t(X,B) cũng phải =6 ở dòng dưới)
        [7.0, 3.0, 6.0, 0.0],    # từ X  (t(X,B)=6 <- nếu để INF ở đây, calculate_delta_time sẽ luôn trả None)
    ]
    cost_matrix = [row[:] for row in time_matrix]  # cost không dùng trong test này, copy tạm

    taxi = Taxi(id=1, depot_node=depot, capacity=100.0)

    dep_A = 5.0       # tính tay ở trên
    old_dep_B = 9.0    # tính tay ở trên

    # --- Case 1: window rộng [0, 20] -> phải chèn được, delta = 7 ---
    parcel_2_wide = ParcelRequest(
        id=2, pickup_node=node_X, dropoff_node=node_X, revenue=0.0,
        early_pickup=0.0, late_pickup=20.0,
        early_dropoff=0.0, late_dropoff=20.0,
        service_time=2.0, weight=0.0,
    )
    instance_wide = ProblemInstance(
        taxis=[taxi], passengers=[], parcels=[parcel_1, parcel_2_wide],
        time_matrix=time_matrix, cost_matrix=cost_matrix,
    )
    delta_case1 = calculate_delta_time(
        dep_A=dep_A, node_A=node_A, node_B=node_B,
        old_dep_B=old_dep_B, insert_node=node_X, instance=instance_wide,
    )
    print(f"Case 1 (window X = [0, 20]): calculate_delta_time trả về = {delta_case1}")
    print(f"  Kỳ vọng (tính tay) = 7.0  ->  {'KHỚP' if delta_case1 is not None and abs(delta_case1 - 7.0) < 1e-6 else 'LỆCH -> CÓ BUG!'}")

    # --- Case 2: window hẹp [0, 6] -> arr_X = 8 > late_X = 6 -> phải trả về None ---
    parcel_2_tight = ParcelRequest(
        id=2, pickup_node=node_X, dropoff_node=node_X, revenue=0.0,
        early_pickup=0.0, late_pickup=6.0,
        early_dropoff=0.0, late_dropoff=6.0,
        service_time=2.0, weight=0.0,
    )
    instance_tight = ProblemInstance(
        taxis=[taxi], passengers=[], parcels=[parcel_1, parcel_2_tight],
        time_matrix=time_matrix, cost_matrix=cost_matrix,
    )
    delta_case2 = calculate_delta_time(
        dep_A=dep_A, node_A=node_A, node_B=node_B,
        old_dep_B=old_dep_B, insert_node=node_X, instance=instance_tight,
    )
    print(f"Case 2 (window X = [0, 6]):  calculate_delta_time trả về = {delta_case2}")
    print(f"  Kỳ vọng (tính tay) = None (arr_X=8 > late_X=6)  ->  {'KHỚP' if delta_case2 is None else 'LỆCH -> CÓ BUG!'}")


# 6: Sinh dữ liệu lớn

def generate_random_instance(
    n_passengers: int,
    n_parcels: int,
    n_taxis: int,
    seed: int = 42
) -> ProblemInstance:
    """Sinh dữ liệu giả lập có quy mô tùy chỉnh."""
    random.seed(seed)

    nodes = [Node(id=0, type='DEPOT', matrix_index=0)]
    node_idx = 1

    passengers = []
    parcels = []

    for i in range(1, n_passengers + 1):
        p_node = Node(id=node_idx, type='PASSENGER_PICKUP', matrix_index=node_idx)
        node_idx += 1
        d_node = Node(id=node_idx, type='PASSENGER_DROPOFF', matrix_index=node_idx)
        node_idx += 1
        nodes.extend([p_node, d_node])

        passengers.append(PassengerRequest(
            id=i, pickup_node=p_node, dropoff_node=d_node,
            revenue=100.0, early_pickup=0.0, late_pickup=1000.0, service_time=2.0
        ))

    for j in range(1, n_parcels + 1):
        p_node = Node(id=node_idx, type='PARCEL_PICKUP', matrix_index=node_idx)
        node_idx += 1
        d_node = Node(id=node_idx, type='PARCEL_DROPOFF', matrix_index=node_idx)
        node_idx += 1
        nodes.extend([p_node, d_node])

        parcels.append(ParcelRequest(
            id=j, pickup_node=p_node, dropoff_node=d_node,
            weight=2.0, revenue=50.0, early_pickup=0.0, late_pickup=1000.0,
            early_dropoff=0.0, late_dropoff=1000.0, service_time=1.0
        ))

    taxis = [Taxi(id=k, depot_node=nodes[0], capacity=10.0) for k in range(1, n_taxis + 1)]

    total_nodes = len(nodes)
    cost_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]
    time_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]

    for r in range(total_nodes):
        for c in range(total_nodes):
            if r != c:
                val = float(random.randint(5, 25))
                cost_matrix[r][c] = val
                time_matrix[r][c] = val / 2.0

    return ProblemInstance(
        taxis=taxis, passengers=passengers, parcels=parcels,
        time_matrix=time_matrix, cost_matrix=cost_matrix
    )


def run_benchmark():
    test_cases = [
        {"name": "Nhỏ (Small)", "passengers": 10, "parcels": 10, "taxis": 3},
        {"name": "Vừa (Medium)", "passengers": 20, "parcels": 20, "taxis": 5},
        {"name": "Lớn (Large)", "passengers": 35, "parcels": 35, "taxis": 8},
    ]

    print("\n" + "-" * 60)
    print("BẮT ĐẦU BENCHMARK GREEDY SOLVER (dữ liệu lớn, ngẫu nhiên)")
    print("-" * 60)
    for case in test_cases:
        p, h, t = case["passengers"], case["parcels"], case["taxis"]
        instance = generate_random_instance(n_passengers=p, n_parcels=h, n_taxis=t)

        start_time = time.time()
        solver = GreedySolver(instance)
        routes = solver.solve()
        elapsed_time = time.time() - start_time

        benefit = calculate_objective_value(routes, instance)
        total_stops = sum(len(r.stops) for r in routes)

        print(f"--- Kịch bản: {case['name']} ({p} Khách, {h} Hàng, {t} Xe) ---")
        print(f"Thời gian chạy: {elapsed_time:.4f} giây")
        print(f"Tổng Lợi Nhuận: {benefit:.2f}")
        print(f"Tổng số điểm dừng đã chèn thành công: {total_stops}/{2 * (p + h)}")
        print("-" * 50)


# Main
def main():
    print("TẠO DỮ LIỆU MẪU NHỎ (2 khách, 2 bưu kiện, 2 xe)")
    instance = generate_demo_instance()
    print_node_table(instance)

    demo_utils(instance)
    demo_validator(instance)
    demo_greedy_solver(instance)
    demo_random_solver(instance)
    demo_hill_climbing(instance)
    demo_evaluator(instance)
    demo_evaluator_delta_time()

    run_benchmark()


if __name__ == "__main__":
    main()