import time
import random

from models import Node, PassengerRequest, ParcelRequest, Taxi, ProblemInstance
from greedy_solver import GreedySolver, calculate_objective_value

def generate_random_instance(
    n_passengers: int, 
    n_parcels: int, 
    n_taxis: int, 
    seed: int = 42
) -> ProblemInstance:
    """Sinh dữ liệu giả lập có quy mô tùy chỉnh."""
    random.seed(seed)
    
    # Depot node
    nodes = [Node(id=0, type='DEPOT', matrix_index=0)]
    node_idx = 1
    
    passengers = []
    parcels = []

    # 1. Sinh Hành khách
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

    # 2. Sinh Bưu kiện
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

    # 3. Sinh Taxis
    taxis = [Taxi(id=k, depot_node=nodes[0], capacity=10.0) for k in range(1, n_taxis + 1)]

    # 4. Sinh Ma trận Thời gian & Chi phí
    total_nodes = len(nodes)
    cost_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]
    time_matrix = [[0.0] * total_nodes for _ in range(total_nodes)]

    for r in range(total_nodes):
        for c in range(total_nodes):
            if r != c:
                val = float(random.randint(5, 25))
                cost_matrix[r][c] = val
                time_matrix[r][c] = val / 2.0  # Tốc độ giả định 2 đơn vị khoảng cách / đơn vị thời gian

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

    print("=== BẮT ĐẦU BENCHMARK GREEDY SOLVER ===")
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
        print(f"Tổng số điểm dừng đã chèn thành công: {total_stops}/{2*(p+h)}")
        print("-" * 50)

if __name__ == "__main__":
    run_benchmark()