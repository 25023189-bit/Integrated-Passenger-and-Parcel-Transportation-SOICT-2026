from typing import List, Optional, Tuple
from models import Node, ProblemInstance

# Làm nhiệm vụ biến đổi cấu trúc danh sách stops (List[Node]),
# Mỗi hàm ở đây nhận vào (các) route hiện tại, trả về route mới (không sửa route cũ
# tại chỗ) để dễ so sánh trước/sau khi tính delta cost/benefit.
#
# "Pair Mode": theo Công thức (7) trong đề bài, một khách hàng luôn phải đi liền cặp
# [Pickup, Dropoff] — không được tách rời trong bất kỳ route nào. Vì vậy mọi thao tác
# di chuyển/hoán đổi một node hành khách đều phải kéo theo node còn lại của cặp đó.
# Bưu kiện thì không bị ràng buộc này nên chỉ di chuyển đúng 1 node.
#
# Phân loại toán tử:
#   - relocate(): toán tử nội 1 xe (intra_route) — di chuyển 1 request trong CÙNG 1 route.
#   - swap():     toán tử giữa các xe (inter_route) — hoán đổi request giữa route1 và route2.
#                 (route1 và route2 có thể là cùng 1 route, khi đó swap() hoạt động
#                  như 1 toán tử intra_route hoán đổi 2 request trong cùng 1 xe.)

def _get_request_block(
    route: List[Node],
    idx: int,
    instance: ProblemInstance
) -> Optional[Tuple[int, int, List[Node]]]:
    """
    Hàm nội bộ (không export): xác định "khối" (block) node cần di chuyển cùng nhau
    khi thao tác lên vị trí idx trong route.

    - Nếu route[idx] là PASSENGER_PICKUP hoặc PASSENGER_DROPOFF: trả về block gồm
      CẢ 2 node liền kề [Pickup, Dropoff] của khách đó (đúng Pair Mode).
    - Nếu route[idx] là bưu kiện (hoặc loại khác): trả về block chỉ gồm chính node đó.

    Trả về (lo, hi, block_nodes):
        lo, hi   : chỉ số đầu/cuối của block trong route gốc (lo <= hi)
        block_nodes: danh sách node theo đúng thứ tự [Pickup, Dropoff] (nếu là khách)

    Trả về None nếu index không hợp lệ, hoặc route không đúng bất biến Công thức (7)
    (ví dụ Pickup/Dropoff của cùng 1 khách không nằm liền kề nhau) — trường hợp này
    coi là lỗi dữ liệu đầu vào, không cố xử lý để tránh làm hỏng route âm thầm.
    """
    if not (0 <= idx < len(route)):
        return None

    node = route[idx]

    if node.type == 'PASSENGER_PICKUP':
        req = instance.get_passenger_by_node(node)
        if req is None:
            return None
        # Theo Công thức (7), Dropoff phải nằm ngay sau Pickup
        if idx + 1 >= len(route) or route[idx + 1].id != req.dropoff_node.id:
            return None
        return idx, idx + 1, [route[idx], route[idx + 1]]

    elif node.type == 'PASSENGER_DROPOFF':
        req = instance.get_passenger_by_node(node)
        if req is None:
            return None
        # Pickup phải nằm ngay trước Dropoff
        if idx - 1 < 0 or route[idx - 1].id != req.pickup_node.id:
            return None
        return idx - 1, idx, [route[idx - 1], route[idx]]

    else:
        # Bưu kiện (hoặc node đơn lẻ khác): không có ràng buộc đi cặp, block = chính nó
        return idx, idx, [node]


def relocate(
    route: List[Node],
    node_idx: int,
    target_idx: int,
    instance: ProblemInstance
) -> Optional[List[Node]]:
    """
    [Toán tử intra_route] Di chuyển 1 request (bưu kiện: 1 node; hành khách: cả cặp
    [Pickup, Dropoff]) từ vị trí node_idx sang vị trí target_idx, trong cùng 1 route.

    Tham số:
        route:      danh sách stops hiện tại của 1 xe (không bị chỉnh sửa tại chỗ)
        node_idx:   vị trí (trong route) của node muốn di chuyển — có thể trỏ vào
                    Pickup hoặc Dropoff của 1 khách, hàm sẽ tự nhận diện và kéo theo
                    node còn lại (Pair Mode)
        target_idx: vị trí muốn chèn block vào, được tính trên route sau khi đã bỏ
                    block cũ ra (tức là index trong danh sách "phần còn lại")
        instance:   dùng để tra request tương ứng với node (get_passenger_by_node)

    Trả về route mới (list Node), hoặc None nếu thao tác không hợp lệ về cấu trúc
    (index sai, hoặc route đầu vào không đúng bất biến Công thức 7).

    Lưu ý: hàm này không kiểm tra ràng buộc thời gian/tải trọng — việc đó do
    evaluator.py / validator.py đảm nhiệm sau khi có route mới.
    """
    block = _get_request_block(route, node_idx, instance)
    if block is None:
        return None
    lo, hi, block_nodes = block

    # Route sau khi loại bỏ block cũ (không đụng route gốc, tạo list mới)
    remaining = route[:lo] + route[hi + 1:]

    if not (0 <= target_idx <= len(remaining)):
        return None

    # Chèn nguyên block vào vị trí target_idx trong phần còn lại
    return remaining[:target_idx] + block_nodes + remaining[target_idx:]


def swap(
    route1: List[Node],
    route2: List[Node],
    node_idx1: int,
    node_idx2: int,
    instance: ProblemInstance
) -> Optional[Tuple[List[Node], List[Node]]]:
    """
    [Toán tử inter_route, dùng được cho cả intra_route khi route1 is route2]
    Hoán đổi request tại vị trí node_idx1 (trong route1) với request tại vị trí
    node_idx2 (trong route2). Nếu 1 trong 2 (hoặc cả 2) là hành khách, hoán đổi
    NGUYÊN CẶP [Pickup, Dropoff] của khách đó (Pair Mode) — không tách lẻ.

    - Nếu route1 và route2 là 2 route khác nhau: đây là toán tử inter_route
      (đổi request giữa 2 xe khác nhau).
    - Nếu route1 is route2 (cùng 1 route): hàm hoạt động như toán tử intra_route,
      hoán đổi vị trí 2 request trong CÙNG 1 xe.

    Trả về (route1_mới, route2_mới), hoặc None nếu thao tác không hợp lệ (index sai,
    route không đúng bất biến, hoặc 2 block được chọn bị chồng lấn khi route1 is route2).
    """
    block1 = _get_request_block(route1, node_idx1, instance)
    block2 = _get_request_block(route2, node_idx2, instance)
    if block1 is None or block2 is None:
        return None

    lo1, hi1, nodes1 = block1
    lo2, hi2, nodes2 = block2

    if route1 is route2:
        # --- Trường hợp intra_route: swap 2 block trong CÙNG 1 danh sách ---
        # Kiểm tra 2 block có dùng chung ít nhất 1 vị trí không (không hợp lệ nếu có)
        if lo1 <= hi2 and lo2 <= hi1:
            return None

        route = route1
        # Sắp lại để block "a" luôn đứng trước block "b" theo chỉ số, cho dễ ghép nối
        if lo1 <= lo2:
            a_lo, a_hi, a_nodes = lo1, hi1, nodes1
            b_lo, b_hi, b_nodes = lo2, hi2, nodes2
        else:
            a_lo, a_hi, a_nodes = lo2, hi2, nodes2
            b_lo, b_hi, b_nodes = lo1, hi1, nodes1

        new_route = (
            route[:a_lo] + b_nodes +           # chỗ của block a giờ chứa nội dung block b
            route[a_hi + 1:b_lo] +             # phần ở giữa 2 block giữ nguyên
            a_nodes +                          # chỗ của block b giờ chứa nội dung block a
            route[b_hi + 1:]
        )
        return new_route, new_route

    else:
        # --- Trường hợp inter_route: 2 route độc lập, không cần lo chồng lấn chỉ số ---
        #
        # chặn 1 trường hợp quan trọng: _get_request_block() trả về block chỉ gồm 1 node
        # cho bưu kiện (vì bưu kiện được phép tách rời pickup/dropoff trong cùng 1 route,
        # nên khác với khách không cần bắt cặp liền kề). Nhưng nếu ta di chuyển đúng 1 node
        # đó (ví dụ chỉ mỗi điểm lấy hàng) sang một xe khác, điểm giao hàng còn lại của
        # đúng bưu kiện đó vẫn nằm ở route cũ -> bưu kiện bị "xẻ đôi" cho 2 xe khác nhau,
        # điều không thể xảy ra trong thực tế (1 xe vật lý mới chở được từ lúc lấy đến lúc giao).
        # Vì vậy: chỉ cho phép swap() giữa 2 route khác nhau khi cả 2 block đều là
        # cặp hành khách (đủ 2 node, đã tự bảo toàn Pair Mode) — từ chối (trả None) nếu
        # có block nào là 1 node bưu kiện đơn lẻ.
        for nodes in (nodes1, nodes2):
            if len(nodes) == 1 and nodes[0].type in ('PARCEL_PICKUP', 'PARCEL_DROPOFF'):
                return None

        new_route1 = route1[:lo1] + nodes2 + route1[hi1 + 1:]
        new_route2 = route2[:lo2] + nodes1 + route2[hi2 + 1:]
        return new_route1, new_route2


# Test
# Khối test dưới đây tự dựng 1 ProblemInstance nhỏ, áp dụng relocate()/swap(),
# rồi dùng is_route_valid() (file validator.py có sẵn, không sửa) để xác nhận
# route sinh ra vẫn giữ đúng cấu trúc bất biến (đặc biệt là Pair Mode).
if __name__ == "__main__":
    from models import PassengerRequest, ParcelRequest, Taxi, Route
    from validator import validate_direct_passenger_flow

    # --- Dựng dữ liệu tối thiểu: đủ node để test relocate/swap, không cần ma trận thật ---
    depot = Node(id=0, type='DEPOT', matrix_index=0)

    pa_p, pa_d = Node(id=1, type='PASSENGER_PICKUP', matrix_index=1), Node(id=2, type='PASSENGER_DROPOFF', matrix_index=2)
    pb_p, pb_d = Node(id=3, type='PASSENGER_PICKUP', matrix_index=3), Node(id=4, type='PASSENGER_DROPOFF', matrix_index=4)
    hc_p, hc_d = Node(id=5, type='PARCEL_PICKUP', matrix_index=5), Node(id=6, type='PARCEL_DROPOFF', matrix_index=6)

    passengers = [
        PassengerRequest(id=1, pickup_node=pa_p, dropoff_node=pa_d, revenue=100.0,
                          early_pickup=0.0, late_pickup=100.0, service_time=1.0),
        PassengerRequest(id=2, pickup_node=pb_p, dropoff_node=pb_d, revenue=80.0,
                          early_pickup=0.0, late_pickup=100.0, service_time=1.0),
    ]
    parcels = [
        ParcelRequest(id=1, pickup_node=hc_p, dropoff_node=hc_d, revenue=60.0, weight=3.0,
                       early_pickup=0.0, late_pickup=100.0, early_dropoff=0.0, late_dropoff=100.0,
                       service_time=1.0),
    ]
    taxi1 = Taxi(id=1, depot_node=depot, capacity=10.0)
    taxi2 = Taxi(id=2, depot_node=depot, capacity=10.0)

    # Ma trận giả (không dùng trong test này, chỉ cần tồn tại để ProblemInstance khởi tạo được)
    n_nodes = 7
    fake_matrix = [[0.0] * n_nodes for _ in range(n_nodes)]

    instance = ProblemInstance(
        taxis=[taxi1, taxi2], passengers=passengers, parcels=parcels,
        time_matrix=fake_matrix, cost_matrix=fake_matrix
    )

    print("=" * 60)
    print("TEST 1: relocate() — di chuyển khách A ra cuối route")
    print("=" * 60)
    route1 = [pa_p, pa_d, hc_p, hc_d]
    print(f"Route trước: {[n.id for n in route1]}")
    new_route1 = relocate(route1, node_idx=0, target_idx=2, instance=instance)  # trỏ vào Pickup của khách A
    print(f"Route sau:   {[n.id for n in new_route1]}")
    check_route = Route(taxi=taxi1, stops=new_route1)
    print(f"Vẫn đúng Pair Mode (Công thức 7)? {validate_direct_passenger_flow(check_route, instance)}")
    print(f"Route gốc route1 có bị đổi không (phải KHÔNG đổi)? {[n.id for n in route1] == [1, 2, 5, 6]}")

    print("\n" + "=" * 60)
    print("TEST 2: relocate() trỏ vào Dropoff — vẫn phải kéo theo cả cặp")
    print("=" * 60)
    route2 = [hc_p, hc_d, pa_p, pa_d]
    print(f"Route trước: {[n.id for n in route2]}")
    new_route2 = relocate(route2, node_idx=3, target_idx=0, instance=instance)  # trỏ vào Dropoff (id=2) của khách A
    print(f"Route sau:   {[n.id for n in new_route2]}")
    check_route2 = Route(taxi=taxi1, stops=new_route2)
    print(f"Vẫn đúng Pair Mode? {validate_direct_passenger_flow(check_route2, instance)}")

    print("\n" + "=" * 60)
    print("TEST 3a: swap() giữa 2 route khác nhau (inter_route) — đổi khách A với khách B")
    print("=" * 60)
    route_x = [pa_p, pa_d]
    route_y = [pb_p, pb_d]
    print(f"route_x trước: {[n.id for n in route_x]}, route_y trước: {[n.id for n in route_y]}")
    new_x, new_y = swap(route_x, route_y, node_idx1=0, node_idx2=1, instance=instance)  # trỏ vào Dropoff của B cũng được
    print(f"route_x sau:   {[n.id for n in new_x]}, route_y sau:   {[n.id for n in new_y]}")
    print(f"Pair Mode ở route_x mới? {validate_direct_passenger_flow(Route(taxi=taxi1, stops=new_x), instance)}")
    print(f"Pair Mode ở route_y mới? {validate_direct_passenger_flow(Route(taxi=taxi2, stops=new_y), instance)}")

    print("\n" + "=" * 60)
    print("TEST 3b: swap() giữa 2 route khác nhau với 1 node bưu kiện đơn lẻ -> phải bị TỪ CHỐI")
    print("=" * 60)
    route_p = [pa_p, pa_d]
    route_q = [hc_p, hc_d]
    print(f"route_p: {[n.id for n in route_p]}, route_q: {[n.id for n in route_q]}")
    result_reject = swap(route_p, route_q, node_idx1=0, node_idx2=0, instance=instance)  # node_idx2=0 -> chỉ mỗi hc_p
    print(f"Kết quả (kỳ vọng None, vì sẽ xẻ đôi bưu kiện C cho 2 xe): {result_reject}")

    print("\n" + "=" * 60)
    print("TEST 4: swap() trong CÙNG 1 route (intra_route) — đổi khách A với khách B")
    print("=" * 60)
    route_z = [pa_p, pa_d, hc_p, hc_d, pb_p, pb_d]
    print(f"Route trước: {[n.id for n in route_z]}")
    new_z1, new_z2 = swap(route_z, route_z, node_idx1=0, node_idx2=4, instance=instance)
    print(f"Route sau:   {[n.id for n in new_z1]}")
    print(f"Pair Mode? {validate_direct_passenger_flow(Route(taxi=taxi1, stops=new_z1), instance)}")

    print("\n" + "=" * 60)
    print("TEST 5: swap() với 2 block chồng lấn -> phải trả về None")
    print("=" * 60)
    result = swap(route_z, route_z, node_idx1=0, node_idx2=1, instance=instance)  # cùng 1 khách A
    print(f"Kết quả (kỳ vọng None): {result}")