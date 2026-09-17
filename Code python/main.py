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

    run_benchmark()


if __name__ == "__main__":
    main()