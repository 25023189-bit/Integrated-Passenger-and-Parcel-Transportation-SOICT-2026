from typing import List, Optional, Tuple
from models import Node, ProblemInstance


def calculate_delta_cost(
    node_A: Node,
    node_B: Node,
    insert_node: Node,
    cost_matrix: List[List[float]]
) -> float:
    a_idx = node_A.matrix_index
    b_idx = node_B.matrix_index
    x_idx = insert_node.matrix_index

    cost_AX = cost_matrix[a_idx][x_idx]
    cost_XB = cost_matrix[x_idx][b_idx]
    cost_AB = cost_matrix[a_idx][b_idx]

    return cost_AX + cost_XB - cost_AB


def calculate_delta_time(
    dep_A: float,
    node_A: Node,
    node_B: Node,
    old_dep_B: float,
    insert_node: Node,
    instance: ProblemInstance
) -> Optional[float]:
    t_matrix = instance.time_matrix
    early_X, late_X, service_X = instance.get_node_time_windows(insert_node)
    arr_X = dep_A + t_matrix[node_A.matrix_index][insert_node.matrix_index]
    
    if arr_X > late_X:
        return None

    start_X = arr_X if arr_X >= early_X else early_X
    dep_X = start_X + service_X

    early_B, late_B, service_B = instance.get_node_time_windows(node_B)
    arr_B_new = dep_X + t_matrix[insert_node.matrix_index][node_B.matrix_index]

    if arr_B_new > late_B:
        return None  

    start_B_new = arr_B_new if arr_B_new >= early_B else early_B
    dep_B_new = start_B_new + service_B

    return dep_B_new - old_dep_B


def check_capacity_delta(
    route_stops: List[Node],
    insert_idx: int,
    insert_node: Node,
    capacity: float,
    current_loads: List[float],
    weight: float
) -> bool:
    if insert_node.type in ['PASSENGER_PICKUP', 'PASSENGER_DROPOFF']:
        return True

    if insert_node.type == 'PARCEL_PICKUP':
        for i in range(insert_idx, len(route_stops)):
            if current_loads[i] + weight > capacity:
                return False

    return True