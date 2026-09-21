import random
import copy
from typing import List, Tuple
from models import Node, ProblemInstance

from evaluator import calculate_delta_cost, calculate_delta_time, check_capacity_delta

# TODO: Sau này sẽ import operators từ nhánh của Hà Thu
# from operators import relocate, swap


class HillClimbingSolver:
    def __init__(self, instance: ProblemInstance, initial_routes: List[List[Node]]):

        self.instance = instance

        self.routes = copy.deepcopy(initial_routes)

        self.MAX_NON_IMPROVING_STEPS = 500

    def solve(self) -> List[List[Node]]:
        """
        Vòng lặp chính của Hill Climbing.
        """
        non_improving_steps = 0
        iteration = 0

        print("Bắt đầu chạy Hill Climbing...")

        
        while non_improving_steps < self.MAX_NON_IMPROVING_STEPS:
            iteration += 1

            mock_result = self._mock_relocate_operator()
            if not mock_result:
                non_improving_steps += 1
                continue
                
            route_idx, insert_idx, node_A, node_B, insert_node = mock_result

            delta_cost = calculate_delta_cost(node_A, node_B, insert_node, self.instance.cost_matrix)
            
            delta_benefit = -delta_cost 

          
            if delta_benefit <= 0:
                non_improving_steps += 1
                continue

            mock_current_loads = [0.0] * len(self.routes[route_idx])
            is_capacity_valid = check_capacity_delta(
                route_stops=self.routes[route_idx],
                insert_idx=insert_idx,
                insert_node=insert_node,
                capacity=self.instance.vehicles[0].capacity, 
                current_loads=mock_current_loads,
                weight=insert_node.weight if insert_node.type == 'PARCEL_PICKUP' else 0.0
            )

            if not is_capacity_valid:
                non_improving_steps += 1
                continue

            delta_time = calculate_delta_time(
                dep_A=0.0, 
                node_A=node_A,
                node_B=node_B,
                old_dep_B=10.0,
                insert_node=insert_node,
                instance=self.instance
            )
            
            if delta_time is None: # Tức là bị vi phạm (đến muộn)
                non_improving_steps += 1
                continue

            print(f"[Iter {iteration}] Tìm thấy nghiệm tốt hơn! Tiết kiệm: {delta_benefit:.2f}")
            
    
            self.routes[route_idx].insert(insert_idx, insert_node)
   
            non_improving_steps = 0 

        print(f"Thuật toán dừng lại sau {iteration} vòng lặp.")
        return self.routes

    def _mock_relocate_operator(self) -> Optional[Tuple[int, int, Node, Node, Node]]:
        if not self.routes:
            return None
            
        route_idx = random.randint(0, len(self.routes) - 1)
        route = self.routes[route_idx]
        
        if len(route) < 2:
            return None


        insert_idx = random.randint(1, len(route) - 1)
        node_A = route[insert_idx - 1]
        node_B = route[insert_idx]
        
        insert_node = Node(id="MOCK", matrix_index=0, type="PASSENGER_PICKUP")
        
        return (route_idx, insert_idx, node_A, node_B, insert_node)