import sys
from pathlib import Path

# 1. Định tuyến đường dẫn tới thư mục src/ trước khi import các module
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.append(str(SRC_DIR))

# 2. Import module từ src/
from models import Node, PassengerRequest, ParcelRequest, Taxi, ProblemInstance
from greedy_solver import GreedySolver, calculate_objective_value
from validator import is_route_valid

def main():
    # 3. Khởi tạo dữ liệu giả lập (Dummy Data) để kiểm thử
    nodes = [
        Node(id=0, type='DEPOT', matrix_index=0),
        Node(id=1, type='PASSENGER_PICKUP', matrix_index=1),
        Node(id=2, type='PASSENGER_DROPOFF', matrix_index=2)
    ]

    taxis = [Taxi(id=1, depot_node=nodes[0], capacity=10.0)]

    passengers = [
        PassengerRequest(
            id=1, 
            pickup_node=nodes[1], 
            dropoff_node=nodes[2], 
            revenue=100.0, 
            early_pickup=0.0, 
            late_pickup=50.0, 
            service_time=2.0
        )
    ]

    parcels = []

    time_matrix = [
        [0.0, 5.0, 10.0], 
        [5.0, 0.0, 5.0], 
        [10.0, 5.0, 0.0]
    ]

    cost_matrix = [
        [0.0, 10.0, 20.0], 
        [10.0, 0.0, 10.0], 
        [20.0, 10.0, 0.0]
    ]

    instance = ProblemInstance(
        taxis=taxis, 
        passengers=passengers, 
        parcels=parcels, 
        time_matrix=time_matrix, 
        cost_matrix=cost_matrix
    )

    # 4. Chạy Greedy Solver
    solver = GreedySolver(instance)
    solution_routes = solver.solve()

    # 5. In kết quả kiểm thử Tuần 1
    print("=== KẾT QUẢ THỰC THI TUẦN 1 ===")
    for route in solution_routes:
        stop_ids = [node.id for node in route.stops]
        valid = is_route_valid(route, instance)
        print(f"Taxi {route.taxi.id} Stops: {stop_ids}")
        print(f"Lộ trình hợp lệ (Is Valid): {valid}")

    total_benefit = calculate_objective_value(solution_routes, instance)
    print(f"Tổng Lợi Nhuận (Total Benefit): {total_benefit:.2f}")

if __name__ == "__main__":
    main()