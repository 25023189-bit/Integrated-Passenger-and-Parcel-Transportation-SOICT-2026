"""Checker độc lập cho SOICT 2026 (không dùng chung code với solution.py).
Dùng:  python checker.py input.txt output.txt   -> in 'OK <benefit>' (exit 0) hoặc 'WA <lý do>' (exit 1)
Định dạng input : K N M / K dòng 'depot Q' / N dòng 'P D E L S T' / M dòng 'P D w Ep Lp Ed Ld S T' / ma trận T / ma trận C
Định dạng output: dòng 1 = Benefit ; K dòng tiếp 'm v1..vm' (đỉnh đánh số từ 1, không ghi depot)."""
import sys

def parse_input(path):
    x = open(path).read().split()
    f = [float(v) for v in x]
    K, N, M = int(f[0]), int(f[1]), int(f[2])
    V = 2 * N + 2 * M + K
    p = 3
    dep = []
    for _ in range(K):
        dep.append((int(f[p]), f[p + 1])); p += 2
    pas = []
    for _ in range(N):
        pas.append(f[p:p + 6]); p += 6
    par = []
    for _ in range(M):
        par.append(f[p:p + 9]); p += 9
    if len(f) != p + 2 * V * V:
        raise ValueError("input sai kích thước: có %d số, cần %d" % (len(f), p + 2 * V * V))
    T = [f[p + i * V:p + (i + 1) * V] for i in range(V)]
    p += V * V
    C = [f[p + i * V:p + (i + 1) * V] for i in range(V)]
    return K, N, M, V, dep, pas, par, T, C


def check(inp, out, tol=1e-6):
    K, N, M, V, dep, pas, par, T, C = parse_input(inp)
    tok = open(out).read().split("\n")
    lines = [l.strip() for l in tok if l.strip()]
    if len(lines) != K + 1:
        return None, "output cần %d dòng, có %d" % (K + 1, len(lines))
    try:
        claimed = float(lines[0])
    except ValueError:
        return None, "dòng 1 không phải số"
    # thông tin từng đỉnh (chỉ số 1..V)
    info = {}
    for i, (pn, dn, e, l, s, t) in enumerate(pas):
        info[int(pn)] = ("PP", i, e, l, s, 0.0)
        info[int(dn)] = ("PD", i, 0.0, float("inf"), s, 0.0)
    for j, (ph, dh, w, ep, lp, ed, ld, s, t) in enumerate(par):
        info[int(ph)] = ("HP", j, ep, lp, s, w)
        info[int(dh)] = ("HD", j, ed, ld, s, w)
    seen, total = set(), 0.0
    for k in range(K):
        a = lines[k + 1].split()
        try:
            m = int(a[0]); st = [int(v) for v in a[1:]]
        except ValueError:
            return None, "route %d: dòng sai định dạng" % (k + 1)
        if len(st) != m:
            return None, "route %d: khai m=%d nhưng có %d đỉnh" % (k + 1, m, len(st))
        u, tm, load = dep[k][0], 0.0, 0.0
        Q = dep[k][1]
        pend = set()
        for idx, v in enumerate(st):
            if v not in info:
                return None, "route %d: đỉnh %d không hợp lệ (depot hoặc ngoài khoảng)" % (k + 1, v)
            if v in seen:
                return None, "đỉnh %d xuất hiện 2 lần" % v
            seen.add(v)
            kind, r, e, l, s, w = info[v]
            arr = tm + T[u - 1][v - 1]
            if arr > l + tol:
                return None, "route %d: đến đỉnh %d lúc %g > L=%g" % (k + 1, v, arr, l)
            if kind == "PP":
                if idx + 1 >= m or st[idx + 1] != int(pas[r][1]):
                    return None, "route %d: khách %d không đi thẳng P->D" % (k + 1, r + 1)
                total += pas[r][5]
            elif kind == "PD":
                if idx == 0 or st[idx - 1] != int(pas[r][0]):
                    return None, "route %d: trả khách %d mà không đón liền trước" % (k + 1, r + 1)
            elif kind == "HP":
                pend.add(r); load += w; total += par[r][8]
                if load > Q + tol:
                    return None, "route %d: quá tải %g > %g" % (k + 1, load, Q)
            else:
                if r not in pend:
                    return None, "route %d: giao bưu kiện %d khi chưa lấy" % (k + 1, r + 1)
                pend.discard(r); load -= w
            tm = max(arr, e) + s
            total -= C[u - 1][v - 1]
            u = v
        if pend:
            return None, "route %d: có bưu kiện lấy mà không giao" % (k + 1)
    # đủ cặp: khách và hàng phải đi trọn cặp (đón có thì trả có)
    for i, (pn, dn, *_r) in enumerate(pas):
        if (int(pn) in seen) != (int(dn) in seen):
            return None, "khách %d phục vụ một nửa" % (i + 1)
    for j, row in enumerate(par):
        if (int(row[0]) in seen) != (int(row[1]) in seen):
            return None, "bưu kiện %d phục vụ một nửa" % (j + 1)
    if abs(total - claimed) > 1e-4 * max(1.0, abs(total)):
        return None, "Benefit khai %g nhưng tính lại %g" % (claimed, total)
    return total, "OK"


if __name__ == "__main__":
    try:
        val, msg = check(sys.argv[1], sys.argv[2])
    except Exception as ex:
        val, msg = None, "lỗi checker: %r" % ex
    if val is None:
        print("WA", msg); sys.exit(1)
    print("OK", int(val) if val == int(val) else val)
