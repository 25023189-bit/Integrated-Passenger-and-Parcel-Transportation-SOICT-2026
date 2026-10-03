import math
import os
import random
import sys
import time

# =============================================================================
# SOICT 2026 - Vận tải tích hợp hành khách + bưu kiện   (BẢN v3: lõi nhanh + Local Search + ALNS)
# Chạy:  python solution_v3.py < input.txt > output.txt
# Cấu trúc file:  Inst (dữ liệu mảng)  ->  State (lời giải + toán tử + cache scan)  ->  greedy
#                 -> local search  ->  ALNS (destroy/repair + SA + trọng số thích nghi)
#                 -> verify  ->  watchdog thời gian  ->  main
# Python 3.8, chỉ dùng thư viện chuẩn.
# =============================================================================

INF = float('inf')
EPS = 1e-7
TIME_LIMIT = float(os.environ.get('SOICT_TL', 250.0))  # ALNS chạy đến mốc này (đề: 300s/test)
POLISH = 8.0       # giây cuối dành cho Local Search "đánh bóng" lời giải tốt nhất
HARD = 282.0       # watchdog: tới mốc này mà chưa xong thì in lời giải tốt nhất rồi thoát
STAT = {'it': 0}
PRM = dict(T0=0.12, T1=0.004, qf=0.30, qcap=14, U=8, p_worst=4.0, p_shaw=3.0, reset=4000, seg=60, rho=0.25, noise=0.0)


class Inst(object):
    """Dữ liệu bài toán dạng MẢNG, đánh chỉ số theo đỉnh 0..V-1 (= số đỉnh của đề - 1).
    Mảng theo đỉnh : E (sớm nhất), L (muộn nhất), S (thời gian phục vụ), W (+w lấy hàng / -w giao hàng),
                     tp (0 depot, 1 đón khách, 2 trả khách, 3 lấy hàng, 4 giao hàng), req (đỉnh -> yêu cầu)
    Mảng theo yêu cầu r : 0..N-1 là khách, N..N+M-1 là bưu kiện; P[r], D[r] (đỉnh), rev[r], w[r], typ[r] (0 khách / 1 hàng)
    Điểm TRẢ khách không có cửa sổ thời gian: E=0, L=INF (chỉ tốn S)."""

    def __init__(s, text):
        lines = [l.split('#')[0].strip() for l in text.splitlines()]
        x = list(map(float, ' '.join(l for l in lines if l).split()))
        K, N, M = int(x[0]), int(x[1]), int(x[2])
        V = 2 * N + 2 * M + K
        s.K, s.N, s.M, s.V, s.R = K, N, M, V, N + M
        pos = 3
        s.depot, s.Q = [], []
        for _ in range(K):
            s.depot.append(int(x[pos]) - 1)
            s.Q.append(x[pos + 1])
            pos += 2
        s.E = [0.0] * V
        s.L = [INF] * V
        s.S = [0.0] * V
        s.W = [0.0] * V
        s.tp = [0] * V
        s.req = [-1] * V
        s.P, s.D, s.rev, s.w, s.typ = [], [], [], [], []
        for _ in range(N):
            p, d = int(x[pos]) - 1, int(x[pos + 1]) - 1
            e, l, sv, t = x[pos + 2:pos + 6]
            pos += 6
            r = len(s.P)
            s.P.append(p); s.D.append(d); s.rev.append(t); s.w.append(0.0); s.typ.append(0)
            s.E[p], s.L[p], s.S[p], s.tp[p], s.req[p] = e, l, sv, 1, r
            s.E[d], s.L[d], s.S[d], s.tp[d], s.req[d] = 0.0, INF, sv, 2, r
        for _ in range(M):
            p, d = int(x[pos]) - 1, int(x[pos + 1]) - 1
            w, ep, lp, ed, ld, sv, t = x[pos + 2:pos + 9]
            pos += 9
            r = len(s.P)
            s.P.append(p); s.D.append(d); s.rev.append(t); s.w.append(w); s.typ.append(1)
            s.E[p], s.L[p], s.S[p], s.W[p], s.tp[p], s.req[p] = ep, lp, sv, w, 3, r
            s.E[d], s.L[d], s.S[d], s.W[d], s.tp[d], s.req[d] = ed, ld, sv, -w, 4, r
        s.T = [x[pos + i * V:pos + (i + 1) * V] for i in range(V)]
        pos += V * V
        s.C = [x[pos + i * V:pos + (i + 1) * V] for i in range(V)]


class State(object):
    """Lời giải + các toán tử cấp REQUEST (API dùng lại cho ALNS):
        scan(r, k)            -> (delta_cost, i, j) vị trí chèn rẻ nhất request r vào route k, hoặc None
        best_insert(r, ks)    -> (delta_cost, k, i, j) tốt nhất trên các route ks (mặc định: tất cả)
        insert(r, k, i, j)    -> chèn thật (khách: cả cặp liền nhau; hàng: pickup sau nodes[i], dropoff sau nodes[j])
        remove(r)             -> gỡ request khỏi route (luôn khả thi về thời gian/tải)
        snap(ks) / restore(s) -> chụp / khôi phục (hoàn tác nước đi)
        benefit()             -> tổng doanh thu - tổng chi phí hiện tại
    routes[k] = danh sách đỉnh (không gồm depot).  where[r] = route đang phục vụ r (-1 nếu chưa phục vụ).
    info[k] = (nodes, dep, ld, lat, cost):  nodes = [depot]+routes[k];  dep[i] = giờ rời nodes[i];
        ld[i] = tải sau nodes[i];  lat[i] = giờ ĐẾN muộn nhất tại nodes[i] mà các điểm sau vẫn hợp lệ."""

    def __init__(s, ins):
        s.ins = ins
        s.routes = [[] for _ in range(ins.K)]
        s.info = [s.evaluate(k, []) for k in range(ins.K)]
        s.where = [-1] * ins.R
        s.revsum = 0.0
        s.ver = list(range(ins.K))      # phiên bản route (duy nhất): cache scan chỉ hợp lệ khi đúng phiên bản
        s.cnt = ins.K
        s.cache = [[None] * ins.K for _ in range(ins.R)]

    def bump(s, k):
        s.cnt += 1
        s.ver[k] = s.cnt

    def scan_c(s, r, k):
        c = s.cache[r][k]
        if c is not None and c[0] == s.ver[k]:
            return c[1]
        x = s.scan(r, k)
        s.cache[r][k] = (s.ver[k], x)
        return x

    def best_c(s, r):
        best = None
        for k in range(s.ins.K):
            x = s.scan_c(r, k)
            if x is not None and (best is None or x[0] < best[0]):
                best = (x[0], k, x[1], x[2])
        return best

    def evaluate(s, k, stops):
        """Mô phỏng route từ đầu (đúng công thức đề). Trả None nếu vi phạm cửa sổ / sức chứa."""
        I = s.ins
        T, C, E, L, S, W = I.T, I.C, I.E, I.L, I.S, I.W
        nodes = [I.depot[k]] + stops
        n = len(nodes)
        cap = I.Q[k] + 1e-9
        dep = [0.0] * n
        ld = [0.0] * n
        t = l = c = 0.0
        u = nodes[0]
        for i in range(1, n):
            v = nodes[i]
            a = t + T[u][v]
            if a > L[v]:
                return None
            t = (a if a >= E[v] else E[v]) + S[v]
            l += W[v]
            if l > cap:
                return None
            c += C[u][v]
            dep[i] = t
            ld[i] = l
            u = v
        lat = [INF] * n
        x = INF
        for i in range(n - 1, 0, -1):
            v = nodes[i]
            la = L[v]
            y = x - S[v]
            if y < la:
                la = y
            lat[i] = la
            x = la - T[nodes[i - 1]][v]
        return (nodes, dep, ld, lat, c)

    def benefit(s):
        return s.revsum - sum(f[4] for f in s.info)

    def scan(s, r, k):
        """Duyệt mọi vị trí chèn hợp lệ của request r vào route k, O(n^2) với bưu kiện, O(n) với khách.
        Dùng 'dep' (mốc thời gian) + 'lat' (độ trễ cho phép) nên mỗi vị trí kiểm tra O(1)."""
        I = s.ins
        T, C, E, L, S, tp = I.T, I.C, I.E, I.L, I.S, I.tp
        nodes, dep, ld, lat, _ = s.info[k]
        n = len(nodes)
        p, d, w = I.P[r], I.D[r], I.w[r]
        cap = I.Q[k] + 1e-9
        Lp, Ep, Sp = L[p], E[p], S[p]
        Ld, Ed, Sd = L[d], E[d], S[d]
        Tp, Cp, Cd = T[p], C[p], C[d]
        parcel = I.typ[r] == 1
        best = INF
        bi = bj = -1
        for i in range(n):
            a = nodes[i]
            if tp[a] == 1:          # không được chen vào giữa chuyến đi trực tiếp của khách
                continue
            ap = dep[i] + T[a][p]
            if ap > Lp or ld[i] + w > cap:
                continue
            t = (ap if ap >= Ep else Ep) + Sp
            ca = C[a][p]
            # (1) dropoff ngay sau pickup (khách bắt buộc kiểu này; hàng cũng thử)
            ad = t + Tp[d]
            if ad <= Ld:
                td = (ad if ad >= Ed else Ed) + Sd
                if i + 1 < n:
                    b = nodes[i + 1]
                    if td + T[d][b] <= lat[i + 1]:
                        dc = ca + Cp[d] + Cd[b] - C[a][b]
                        if dc < best:
                            best, bi, bj = dc, i, i
                else:
                    dc = ca + Cp[d]
                    if dc < best:
                        best, bi, bj = dc, i, i
            if not parcel or i + 1 >= n:
                continue
            # (2) bưu kiện: dropoff sau nodes[m] (m > i), pickup làm trễ các điểm giữa -> mô phỏng tiến
            s1 = nodes[i + 1]
            cpick = ca + Cp[s1] - C[a][s1]
            cur, tc = p, t
            for m in range(i + 1, n):
                v = nodes[m]
                arr = tc + T[cur][v]
                if arr > L[v] or ld[m] + w > cap:
                    break           # từ đây trở đi mọi vị trí dropoff đều vi phạm
                tc = (arr if arr >= E[v] else E[v]) + S[v]
                cur = v
                if tp[v] == 1:
                    continue
                ad = tc + T[v][d]
                if ad > Ld:
                    continue
                td = (ad if ad >= Ed else Ed) + Sd
                if m + 1 < n:
                    b = nodes[m + 1]
                    if td + T[d][b] <= lat[m + 1]:
                        dc = cpick + C[v][d] + Cd[b] - C[v][b]
                        if dc < best:
                            best, bi, bj = dc, i, m
                else:
                    dc = cpick + C[v][d]
                    if dc < best:
                        best, bi, bj = dc, i, m
        if bi < 0:
            return None
        return (best, bi, bj)

    def best_insert(s, r, ks=None):
        best = None
        for k in (range(s.ins.K) if ks is None else ks):
            x = s.scan(r, k)
            if x is not None and (best is None or x[0] < best[0]):
                best = (x[0], k, x[1], x[2])
        return best

    def insert(s, r, k, i, j):
        I = s.ins
        st = s.routes[k]
        new = st[:i] + [I.P[r]] + st[i:j] + [I.D[r]] + st[j:]
        f = s.evaluate(k, new)
        if f is None:
            return False
        s.routes[k] = new
        s.info[k] = f
        s.bump(k)
        s.where[r] = k
        s.revsum += I.rev[r]
        return True

    def remove(s, r):
        I = s.ins
        k = s.where[r]
        p, d = I.P[r], I.D[r]
        new = [v for v in s.routes[k] if v != p and v != d]
        f = s.evaluate(k, new)
        if f is None:
            return False
        s.routes[k] = new
        s.info[k] = f
        s.bump(k)
        s.where[r] = -1
        s.revsum -= I.rev[r]
        return True

    def remove_many(s, rs):
        """Gỡ nhiều request cùng lúc (mỗi route chỉ dựng lại 1 lần). Trả False (không đổi gì) nếu lỗi."""
        I = s.ins
        by = {}
        for r in rs:
            by.setdefault(s.where[r], []).append(r)
        new = {}
        for k, lst in by.items():
            drop = set()
            for r in lst:
                drop.add(I.P[r])
                drop.add(I.D[r])
            stops = [v for v in s.routes[k] if v not in drop]
            f = s.evaluate(k, stops)
            if f is None:
                return False
            new[k] = (stops, f)
        for k, (stops, f) in new.items():
            s.routes[k] = stops
            s.info[k] = f
            s.bump(k)
        for r in rs:
            s.where[r] = -1
            s.revsum -= I.rev[r]
        return True

    def snap(s, ks):
        return (list(s.where), s.revsum, [(k, s.routes[k], s.info[k], s.ver[k]) for k in ks])

    def restore(s, sn):
        s.where[:] = sn[0]
        s.revsum = sn[1]
        for k, rt, f, v in sn[2]:
            s.routes[k] = rt
            s.info[k] = f
            s.ver[k] = v


# ----------------------------------------------------------------------------- Greedy
def greedy(st, deadline):
    """Chèn tham lam: mỗi vòng chọn (request, route, vị trí) có lợi nhuận (doanh thu - delta cost) lớn nhất.
    Cache kết quả scan theo (request, route); chỉ tính lại route vừa thay đổi."""
    I = st.ins
    R, K = I.R, I.K
    bst = [[st.scan(r, k) for k in range(K)] for r in range(R)]
    while time.time() < deadline:
        bg = EPS
        pick = None
        for r in range(R):
            if st.where[r] >= 0:
                continue
            rv = I.rev[r]
            row = bst[r]
            for k in range(K):
                x = row[k]
                if x is not None and rv - x[0] > bg:
                    bg = rv - x[0]
                    pick = (r, k, x[1], x[2])
        if pick is None:
            break
        r, k, i, j = pick
        if not st.insert(r, k, i, j):
            bst[r][k] = None
            continue
        for r2 in range(R):
            if st.where[r2] < 0:
                bst[r2][k] = st.scan(r2, k)


# ----------------------------------------------------------------------------- Toán tử Local Search
# Mỗi toán tử trả True nếu đã cải thiện benefit (và giữ nguyên thay đổi), ngược lại hoàn tác và trả False.
def add_unserved(st, r):
    """Chèn request chưa phục vụ vào vị trí rẻ nhất nếu có lời."""
    x = st.best_insert(r)
    if x is not None and st.ins.rev[r] - x[0] > EPS:
        return st.insert(r, x[1], x[2], x[3])
    return False


def relocate(st, r):
    """Gỡ r rồi chèn lại vào vị trí tốt nhất ở BẤT KỲ xe nào (gồm cả đổi vị trí trong cùng xe).
    Nếu r đang lỗ (doanh thu < chi phí phải trả thêm) thì thả luôn (drop)."""
    I = st.ins
    base = st.benefit()
    sn = st.snap([st.where[r]])
    if not st.remove(r):
        return False
    after = st.benefit()
    x = st.best_insert(r)
    if x is not None and I.rev[r] - x[0] > 0:
        if after + I.rev[r] - x[0] > base + EPS and st.insert(r, x[1], x[2], x[3]):
            return True
    elif after > base + EPS:
        return True                 # r đang kéo lợi nhuận xuống -> bỏ đơn
    st.restore(sn)
    return False


def swap(st, r1, r2):
    """Hoán đổi 2 request đang phục vụ: r1 sang xe của r2 và ngược lại (cùng xe thì xếp lại cả 2)."""
    a, b = st.where[r1], st.where[r2]
    base = st.benefit()
    sn = st.snap({a, b})
    if st.remove(r1) and st.remove(r2):
        x = st.scan(r1, b)
        if x is not None and st.insert(r1, b, x[1], x[2]):
            y = st.scan(r2, a)
            if y is not None and st.insert(r2, a, y[1], y[2]) and st.benefit() > base + EPS:
                return True
    st.restore(sn)
    return False


def replace(st, ro, ri):
    """Thay đơn ro (đang phục vụ) bằng đơn ri (chưa phục vụ) ngay trên xe của ro, rồi chèn lại ro ở nơi tốt nhất."""
    I = st.ins
    k0 = st.where[ro]
    base = st.benefit()
    sn = st.snap([k0])
    if st.remove(ro):
        x = st.scan(ri, k0)
        if x is not None and I.rev[ri] - x[0] > 0 and st.insert(ri, k0, x[1], x[2]):
            y = st.best_insert(ro)
            if y is not None and I.rev[ro] - y[0] > 0:
                if st.benefit() + I.rev[ro] - y[0] > base + EPS and st.insert(ro, y[1], y[2], y[3]):
                    return True
            elif st.benefit() > base + EPS:
                return True
    st.restore(sn)
    return False


def local_search(st, deadline, rng):
    """Hill Climbing đến khi không còn nước đi cải thiện (hoặc hết giờ):
    vòng 1: relocate/add/drop từng request  ->  vòng 2: swap cặp + replace (chỉ khi vòng 1 hết cải thiện)."""
    R = st.ins.R
    while time.time() < deadline:
        imp = False
        order = list(range(R))
        rng.shuffle(order)
        for r in order:
            if time.time() > deadline:
                return
            if st.where[r] < 0:
                imp |= add_unserved(st, r)
            else:
                imp |= relocate(st, r)
        if imp:
            continue
        sv = [r for r in range(R) if st.where[r] >= 0]
        un = [r for r in range(R) if st.where[r] < 0]
        rng.shuffle(sv)
        rng.shuffle(un)
        for x in range(len(sv)):
            r1 = sv[x]
            for y in range(x + 1, len(sv)):
                if time.time() > deadline:
                    return
                r2 = sv[y]
                if st.where[r1] >= 0 and st.where[r2] >= 0 and swap(st, r1, r2):
                    imp = True
            for u in un:
                if time.time() > deadline:
                    return
                if st.where[u] < 0 and st.where[r1] >= 0 and replace(st, r1, u):
                    imp = True
        if not imp:
            return


# ----------------------------------------------------------------------------- ALNS
# Destroy: (st, q, rng, sv, un) -> (removed, extra) hoặc None.  removed = đã gỡ khỏi lời giải; extra = đơn chưa phục vụ
# được "mời" vào pool sửa (hạt giống Shaw).  Repair: (st, pool, rng) chèn lại các request trong pool.
def _pick(cand, q, rng, p):
    """Lấy q phần tử đầu danh sách đã sắp, có ngẫu nhiên hoá (p lớn -> càng bám sát đầu danh sách)."""
    out = []
    while len(out) < q and cand:
        out.append(cand.pop(int(len(cand) * rng.random() ** p))[1])
    return out


def d_random(st, q, rng, sv, un):
    rs = rng.sample(sv, min(q, len(sv)))
    return (rs, []) if st.remove_many(rs) else None


def d_worst(st, q, rng, sv, un):
    """Gỡ các request đóng góp lợi nhuận kém nhất (doanh thu - chi phí đường vòng mà request gây ra)."""
    I = st.ins
    C, tp = I.C, I.tp
    sav = {}
    for k in range(I.K):
        nodes = st.info[k][0]
        n = len(nodes)
        for i in range(1, n):
            v = nodes[i]
            r = I.req[v]
            a = nodes[i - 1]
            t = tp[v]
            if t == 1 or t == 3:
                d = I.D[r]
                if i + 1 < n and nodes[i + 1] == d:
                    b = nodes[i + 2] if i + 2 < n else -1
                    sav[r] = C[a][v] + C[v][d] + (C[d][b] - C[a][b] if b >= 0 else 0.0)
                else:
                    b = nodes[i + 1] if i + 1 < n else -1
                    sav[r] = C[a][v] + (C[v][b] - C[a][b] if b >= 0 else 0.0)
            elif a != I.P[r]:
                b = nodes[i + 1] if i + 1 < n else -1
                sav[r] = sav.get(r, 0.0) + C[a][v] + (C[v][b] - C[a][b] if b >= 0 else 0.0)
    cand = sorted((I.rev[r] - x, r) for r, x in sav.items())
    rs = _pick(cand, q, rng, PRM['p_worst'])
    return (rs, []) if st.remove_many(rs) else None


def d_shaw(st, q, rng, sv, un, from_unserved):
    """Gỡ các request 'gần' một request hạt giống (gần về không gian + thời gian). Hạt giống chưa phục vụ
    -> tạo chỗ trống cho nó (rất hợp bài toán chọn đơn); hạt giống đã phục vụ -> gỡ cả nhóm lân cận rồi sắp lại."""
    I = st.ins
    T, E, P, D = I.T, I.E, I.P, I.D
    if from_unserved and un:
        seed, extra = rng.choice(un), True
    else:
        seed, extra = rng.choice(sv), False
    ps, ds = P[seed], D[seed]
    es = E[ps]
    inv_t, inv_s = 0.5 / I.avgT, 1.0 / I.tsc
    cand = sorted(((T[ps][P[r]] + T[ds][D[r]]) * inv_t + abs(es - E[P[r]]) * inv_s, r) for r in sv if r != seed)
    rs = _pick(cand, q - (0 if extra else 1), rng, PRM['p_shaw'])
    if not extra:
        rs.insert(0, seed)
    if not st.remove_many(rs):
        return None
    return (rs, [seed] if extra else [])


def r_greedy(st, pool, rng):
    """Mỗi vòng chèn (request, vị trí) có lợi nhuận lớn nhất; dừng khi không còn chèn nào có lời.
    Giữ bảng ứng viên cand[r][k] và chỉ quét lại cột của route vừa thay đổi."""
    I = st.ins
    K, rev, nz = I.K, I.rev, PRM['noise']
    cand = {r: [st.scan_c(r, k) for k in range(K)] for r in pool}
    while cand:
        best = None
        for r, row in cand.items():
            bx = None
            for k in range(K):
                x = row[k]
                if x is not None and (bx is None or x[0] < bx[0]):
                    bx, bk = x, k
            if bx is None:
                continue
            g = rev[r] - bx[0]
            if nz:
                g += rng.uniform(-nz, nz)
            if g > EPS and (best is None or g > best[0]):
                best = (g, r, bk, bx)
        if best is None:
            return
        _, r, k, x = best
        del cand[r]
        if st.insert(r, k, x[1], x[2]):
            for r2, row in cand.items():
                row[k] = st.scan_c(r2, k)


def r_regret(st, pool, rng, m):
    """Regret-m: ưu tiên request mà nếu để trễ sẽ 'mất' nhiều nhất (chênh giữa xe tốt nhất và các xe sau)."""
    I = st.ins
    K, rev = I.K, I.rev
    cand = {r: [st.scan_c(r, k) for k in range(K)] for r in pool}
    while cand:
        best = None
        for r, row in cand.items():
            gs = sorted(((rev[r] - x[0], k) for k, x in enumerate(row) if x is not None), reverse=True)
            if not gs or gs[0][0] <= EPS:
                continue
            g1 = gs[0][0]
            reg = sum(g1 - gs[i][0] for i in range(1, min(m, len(gs)))) + 1e6 * max(0, m - len(gs))
            if best is None or (reg, g1) > best[0]:
                best = ((reg, g1), r, gs[0][1])
        if best is None:
            return
        _, r, k = best
        x = cand.pop(r)[k]
        if st.insert(r, k, x[1], x[2]):
            for r2, row in cand.items():
                row[k] = st.scan_c(r2, k)


def _roulette(w, rng):
    x = rng.random() * sum(w)
    for i, v in enumerate(w):
        x -= v
        if x <= 0:
            return i
    return len(w) - 1


def alns(st, deadline, rng, on_best):
    """ALNS: mỗi vòng chọn 1 destroy + 1 repair theo trọng số thích nghi, chấp nhận nghiệm theo Simulated Annealing
    (nhiệt độ giảm hình học theo THỜI GIAN), giữ nghiệm tốt nhất, quay về nghiệm tốt nhất khi bí quá lâu."""
    I = st.ins
    R, K, V = I.R, I.K, I.V
    if R == 0:
        return
    I.avgT = max(1.0, sum(map(sum, I.T)) / (V * V))
    I.tsc = max([1.0] + [x for x in I.L if x < INF])
    avg_rev = sum(I.rev) / R
    T0, T1 = PRM['T0'] * avg_rev, PRM['T1'] * avg_rev
    destroys = [d_random, d_worst, lambda *a: d_shaw(*a, False), lambda *a: d_shaw(*a, True)]
    repairs = [r_greedy, lambda *a: r_regret(*a, 2), lambda *a: r_regret(*a, 3)]
    wd, wr = [1.0] * len(destroys), [1.0] * len(repairs)
    sd, sr = [0.0] * len(destroys), [0.0] * len(repairs)
    nd, nr = [0] * len(destroys), [0] * len(repairs)
    cur = best = st.benefit()
    best_sn = st.snap(range(K))
    t_start = time.time()
    span = max(1e-9, deadline - t_start)
    it = last_best = 0
    while True:
        now = time.time()
        if now >= deadline or it - last_best > 200000:
            break
        it += 1
        temp = T0 * (T1 / T0) ** ((now - t_start) / span)
        sv = [r for r in range(R) if st.where[r] >= 0]
        un = [r for r in range(R) if st.where[r] < 0]
        di, ri = _roulette(wd, rng), _roulette(wr, rng)
        sn = st.snap(range(K))
        removed, extra = [], []
        if sv:
            q = rng.randint(1, max(2, min(PRM['qcap'], int(PRM['qf'] * len(sv)))))
            res = destroys[di](st, min(q, len(sv)), rng, sv, un)
            if res is None:
                continue
            removed, extra = res
        pool = removed + extra
        rest = [r for r in un if r not in extra]
        if rest:
            pool += rng.sample(rest, min(len(rest), PRM['U']))
        repairs[ri](st, pool, rng)
        new = st.benefit()
        sc = 0.0
        if new > best + EPS:
            best = new
            best_sn = st.snap(range(K))
            on_best(st)
            last_best = it
            sc = 33.0
        if new > cur + EPS:
            cur = new
            sc = max(sc, 9.0)
        elif new >= cur - EPS or rng.random() < math.exp((new - cur) / temp):
            cur = new
            sc = max(sc, 3.0 if abs(new - cur) > EPS else 1.0)
        else:
            st.restore(sn)
        sd[di] += sc; sr[ri] += sc; nd[di] += 1; nr[ri] += 1
        if it % PRM['seg'] == 0:
            rho = PRM['rho']
            for w, sc_, n_ in ((wd, sd, nd), (wr, sr, nr)):
                for i in range(len(w)):
                    if n_[i]:
                        w[i] = max(0.05, (1 - rho) * w[i] + rho * sc_[i] / n_[i])
                    sc_[i] = 0.0
                    n_[i] = 0
        if it - last_best > PRM['reset']:
            st.restore(best_sn)
            cur = best
            last_best = it
    STAT['it'] = it
    st.restore(best_sn)


# ----------------------------------------------------------------------------- Kiểm tra độc lập + I/O
def verify(I, routes):
    """Kiểm tra lời giải từ đầu theo đúng đề; trả Benefit, hoặc None nếu có vi phạm."""
    seen = set()
    total = 0.0
    for k, stops in enumerate(routes):
        u, t, l = I.depot[k], 0.0, 0.0
        pend = set()
        n = len(stops)
        for i, v in enumerate(stops):
            if v in seen or I.tp[v] == 0:
                return None
            seen.add(v)
            a = t + I.T[u][v]
            if a > I.L[v]:
                return None
            tv, r = I.tp[v], I.req[v]
            if tv == 1:
                if i + 1 >= n or stops[i + 1] != I.D[r]:
                    return None
                total += I.rev[r]
            elif tv == 2:
                if i == 0 or stops[i - 1] != I.P[r]:
                    return None
            elif tv == 3:
                pend.add(r)
                total += I.rev[r]
            else:
                if r not in pend:
                    return None
                pend.discard(r)
            l += I.W[v]
            if l > I.Q[k] + 1e-9:
                return None
            t = (a if a >= I.E[v] else I.E[v]) + I.S[v]
            total -= I.C[u][v]
            u = v
        if pend:
            return None
    return total


def fmt(x):
    return str(int(round(x))) if abs(x - round(x)) < 1e-9 else '%.6f' % x


HOLD = {'routes': None, 'safe': None}
DONE = [False]


def record(st):
    HOLD['routes'] = list(st.routes)      # route không bao giờ bị sửa tại chỗ -> chụp nông là đủ


def finish(I, outfile):
    """In lời giải tốt nhất đã kiểm tra hợp lệ (chỉ in 1 lần, dù gọi từ luồng chính hay từ watchdog)."""
    if DONE[0]:
        return
    DONE[0] = True
    val, routes = 0.0, [[] for _ in range(I.K)]
    for cand in (HOLD['routes'], HOLD['safe']):
        if cand is not None:
            try:
                v = verify(I, cand)
            except Exception:
                v = None
            if v is not None:
                val, routes = v, cand
                break
    out = [fmt(val)] + [' '.join([str(len(r))] + [str(v + 1) for v in r]) for r in routes]
    res = '\n'.join(out) + '\n'
    if outfile:
        with open(outfile, 'w') as f:
            f.write(res)
    else:
        sys.stdout.write(res)
        sys.stdout.flush()


def solve(I, t0):
    rng = random.Random(12345)
    st = State(I)
    deadline = t0 + TIME_LIMIT
    greedy(st, deadline)
    HOLD['safe'] = list(st.routes)
    record(st)
    try:
        local_search(st, deadline, rng)
        record(st)
        alns(st, deadline, rng, record)
        local_search(st, deadline + min(POLISH, 0.04 * TIME_LIMIT), rng)
        if st.benefit() >= (verify(I, HOLD['routes']) or -INF) - EPS:
            record(st)
    except Exception:
        pass


def arm_watchdog(I, outfile, t0):
    """Hẹn giờ cứng bằng SIGALRM (không dùng luồng: nhiều máy chấm cấm tạo luồng). Lỗi gì cũng bỏ qua."""
    try:
        import signal

        def handler(signum, frame):
            if not DONE[0]:
                finish(I, outfile)
                sys.stdout.flush()
                os._exit(0)

        signal.signal(signal.SIGALRM, handler)
        signal.setitimer(signal.ITIMER_REAL, max(1.0, HARD - (time.time() - t0)))
    except Exception:
        pass


def main():
    t0 = time.time()
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    text = open(args[0]).read() if args else sys.stdin.read()
    I = Inst(text)
    outfile = args[1] if len(args) > 1 else None
    arm_watchdog(I, outfile, t0)
    try:
        solve(I, t0)
    except BaseException:
        pass
    finish(I, outfile)


if __name__ == '__main__':
    main()