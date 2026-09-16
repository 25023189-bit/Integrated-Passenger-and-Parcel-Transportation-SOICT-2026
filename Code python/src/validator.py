from models import Route, ProblemInstance
import math

def validate_temporal_flow(route: Route, instance: ProblemInstance) -> bool:
    stops = route.stops
    if not stops:
        return True
    
    dep_u = 0.0 
    u_idx = route.taxi.depot_node.matrix_index
    time_matrix = instance.time_matrix 
    
    for node in stops:
        v_idx = node.matrix_index
        early_v, late_v, service_v = instance.get_node_time_windows(node)
        
        arr_v = dep_u + time_matrix[u_idx][v_idx]
        
        if arr_v > late_v:
            return False 
            
        srv_v = arr_v if arr_v >= early_v else early_v
        dep_u = srv_v + service_v
        u_idx = v_idx
        
    return True

def validate_spatial_flow(route: Route, instance: ProblemInstance) -> bool:
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

    if not (0 <= u_idx < num_nodes and 0 <= v_idx < num_nodes):
        return False

    if math.isinf(cost_matrix[u_idx][v_idx]) or math.isinf(time_matrix[u_idx][v_idx]):
        return False

    for i in range(len(stops) - 1):
        curr_idx = stops[i].matrix_index
        next_idx = stops[i + 1].matrix_index

        if not (0 <= curr_idx < num_nodes and 0 <= next_idx < num_nodes):
            return False

        if math.isinf(cost_matrix[curr_idx][next_idx]) or math.isinf(time_matrix[curr_idx][next_idx]):
            return False

    return True

def validate_capacity_flow(route: Route, instance: ProblemInstance) -> bool:
    stops = route.stops
    if not stops:
        return True 

    capacity = route.taxi.capacity
    current_load = 0.0 

    for node in stops:
        if node.type == 'PARCEL_PICKUP':
            parcel = instance.get_parcel_by_node(node)
            if parcel is None: return False
            
            current_load += parcel.weight
            if current_load > capacity:
                return False

        elif node.type == 'PARCEL_DROPOFF':
            parcel = instance.get_parcel_by_node(node)
            if parcel is None: return False
            
            current_load -= parcel.weight
            if current_load < -1e-7:
                return False

    if current_load > 1e-7:
        return False 

    return True

def validate_direct_passenger_flow(route: Route, instance: ProblemInstance) -> bool:
    stops = route.stops
    if not stops:
        return True

    n_stops = len(stops)
    for i, node in enumerate(stops):
        if node.type == 'PASSENGER_PICKUP':
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None: return False
            
            if i + 1 >= n_stops:
                return False 
                
            next_node = stops[i + 1]
            if next_node.id != passenger_req.dropoff_node.id:
                return False

        elif node.type == 'PASSENGER_DROPOFF':
            passenger_req = instance.get_passenger_by_node(node)
            if passenger_req is None: return False
            
            if i == 0:
                return False
                
            prev_node = stops[i - 1]
            if prev_node.id != passenger_req.pickup_node.id:
                return False

    return True

def validate_time_windows_and_precedence(route: Route, instance: ProblemInstance) -> bool:
    stops = route.stops
    if not stops:
        return True

    current_time = 0.0
    current_node = route.taxi.depot_node
    picked_up_parcels = set()

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
            if req is None: return False
            start_service = arrival_time
            departure_time = start_service + req.service_time

        elif node.type == 'PARCEL_PICKUP':
            req = instance.get_parcel_by_node(node)
            if req is None or arrival_time > req.late_pickup:
                return False
            start_service = max(arrival_time, req.early_pickup)
            departure_time = start_service + req.service_time
            picked_up_parcels.add(req.id)

        elif node.type == 'PARCEL_DROPOFF':
            req = instance.get_parcel_by_node(node)
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
    """
    stops = route.stops
    if not stops:
        return True

    time_matrix = instance.time_matrix
    cost_matrix = instance.cost_matrix
    num_nodes = len(cost_matrix)
    capacity = route.taxi.capacity
    n_stops = len(stops)

    current_time = 0.0
    current_load = 0.0
    current_node = route.taxi.depot_node
    picked_up_parcels = set()

    for i, node in enumerate(stops):
        u_idx = current_node.matrix_index
        v_idx = node.matrix_index

        # 1. Luồng không gian
        if not (0 <= u_idx < num_nodes and 0 <= v_idx < num_nodes): return False
        if math.isinf(cost_matrix[u_idx][v_idx]) or math.isinf(time_matrix[u_idx][v_idx]): return False

        arrival_time = current_time + time_matrix[u_idx][v_idx]
        node_type = node.type

        # 2. Chi tiết từng ràng buộc theo loại nút
        if node_type == 'PASSENGER_PICKUP':
            req = instance.get_passenger_by_node(node)
            if not req or arrival_time > req.late_pickup: return False
            if i + 1 >= n_stops or stops[i + 1].id != req.dropoff_node.id: return False
            start_service = arrival_time if arrival_time >= req.early_pickup else req.early_pickup
            current_time = start_service + req.service_time

        elif node_type == 'PASSENGER_DROPOFF':
            req = instance.get_passenger_by_node(node)
            if not req or i == 0 or stops[i - 1].id != req.pickup_node.id: return False
            current_time = arrival_time + req.service_time

        elif node_type == 'PARCEL_PICKUP':
            req = instance.get_parcel_by_node(node)
            if not req or arrival_time > req.late_pickup: return False
            
            current_load += req.weight
            if current_load > capacity: return False
            
            picked_up_parcels.add(req.id)
            start_service = arrival_time if arrival_time >= req.early_pickup else req.early_pickup
            current_time = start_service + req.service_time

        elif node_type == 'PARCEL_DROPOFF':
            req = instance.get_parcel_by_node(node)
            if not req or req.id not in picked_up_parcels or arrival_time > req.late_dropoff: return False
            
            current_load -= req.weight
            if current_load < -1e-7: return False
            
            picked_up_parcels.remove(req.id)
            start_service = arrival_time if arrival_time >= req.early_dropoff else req.early_dropoff
            current_time = start_service + req.service_time
        else:
            return False

        current_node = node

    # 3. Bảo toàn cuối chuyến
    if current_load > 1e-7 or len(picked_up_parcels) > 0:
        return False

    return True