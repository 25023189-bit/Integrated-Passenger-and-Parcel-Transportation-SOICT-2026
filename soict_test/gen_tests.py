"""Sinh bộ test cực đoan + test lớn cho SOICT 2026 (xác định theo seed, chỉ dùng thư viện chuẩn).
Dùng:  python gen_tests.py [--out tests] [--seed 2026] [--only chuoi] [--skip-big] [--list]
Mỗi test ghi ra NAME.txt (input) và NAME.json (meta: kích thước, đáp án chính xác nếu biết trước)."""
import argparse, json, math, os, random

DEF = dict(G=100, H=100, win="normal", rev=(30, 550), Q=(20, 30), w=(5, 15), S=(2, 5), mat="euclid", expect=None, note="")
SC = {}


def sc(name, K, N, M, **kw):
    d = dict(DEF); d.update(K=K, N=N, M=M); d.update(kw); SC[name] = d


# --- cỡ nhỏ / K=1 / chỉ một loại yêu cầu --------------------------------------------------------
sc("k1_small", 1, 8, 8, note="K=1, nhỏ")
sc("k1_mid", 1, 60, 60, note="K=1, một xe phải chọn đơn")
sc("k1_big", 1, 300, 300, note="K=1, 600 yêu cầu")
sc("only_pass_mid", 5, 40, 0, note="toàn khách (M=0)")
sc("only_pass_big", 60, 300, 0, note="toàn khách, N=300")
sc("only_parcel_mid", 5, 0, 40, note="toàn bưu kiện (N=0)")
sc("only_parcel_big", 60, 0, 300, note="toàn bưu kiện, M=300")
sc("no_requests", 3, 0, 0, expect=0, note="N=M=0 (ngoài đặc tả, kiểm tra không crash)")
# --- cửa sổ thời gian ----------------------------------------------------------------------------
sc("win_tight_mid", 10, 50, 50, win="tight", note="cửa sổ rộng 0-2, neo theo khoảng cách từ depot")
sc("win_tight_big", 100, 300, 300, win="tight")
sc("win_point_mid", 10, 50, 50, win="point", note="E = L (cửa sổ độ rộng 0)")
sc("win_wide_mid", 10, 50, 50, win="wide", note="L = 100000")
sc("win_wide_big", 100, 300, 300, win="wide", note="cửa sổ rất rộng: không gian tìm kiếm lớn nhất")
sc("win_wide_k1", 1, 100, 100, win="wide", note="1 xe, cửa sổ rất rộng: route rất dài")
sc("dense_peak", 20, 150, 150, H=10, note="mọi E trong [0,10]: tranh chấp tài nguyên cao")
# --- kinh tế -------------------------------------------------------------------------------------
sc("no_profit_mid", 10, 50, 50, rev=(1, 1), expect=0, note="không đơn nào có lời: đáp án đúng = 0")
sc("no_profit_big", 100, 300, 300, rev=(1, 1), expect=0)
sc("infeasible_all", 10, 50, 50, win="impossible", expect=0, note="mọi cửa sổ không với tới được: đáp án = 0")
sc("huge_revenue", 10, 50, 50, rev=(10 ** 6, 10 ** 7), note="doanh thu rất lớn: phục vụ tối đa")
sc("long_service", 10, 60, 60, S=(30, 60), note="thời gian phục vụ dài")
# --- sức chứa ------------------------------------------------------------------------------------
sc("cap_equal", 10, 30, 80, Q=(10, 10), w=(10, 10), note="w = Q: mỗi lần chở đúng 1 bưu kiện")
sc("cap_one", 20, 20, 150, Q=(1, 1), w=(1, 1), note="Q=1")
sc("cap_too_small", 10, 40, 40, Q=(1, 1), w=(2, 2), note="mọi bưu kiện nặng hơn sức chứa: chỉ còn khách")
# --- ma trận -------------------------------------------------------------------------------------
sc("zero_dist", 5, 40, 40, mat="zero", win="wide", expect="sumrev", note="mọi khoảng cách = 0: đáp án = tổng doanh thu")
sc("asym_mid", 10, 50, 50, mat="asym", note="T, C bất đối xứng, C độc lập với T, vi phạm bất đẳng thức tam giác")
sc("asym_big", 80, 250, 250, mat="asym")
# --- cỡ lớn --------------------------------------------------------------------------------------
sc("many_vehicles", 300, 10, 10, note="xe nhiều hơn yêu cầu")
sc("real_like_xl", 30, 250, 250, note="giống test thật nhưng lớn hơn")
sc("big_normal", 100, 300, 300, note="K,N,M hàng trăm, cửa sổ như test thật")
sc("huge", 200, 300, 300, note="V=1400: kiểm tra RAM/thời gian đọc input")


def nverts(p):
    return 2 * p["N"] + 2 * p["M"] + p["K"]


def make(name, p, seed):
    rnd = random.Random("%s:%s" % (seed, name))
    K, N, M, G, H = p["K"], p["N"], p["M"], p["G"], p["H"]
    V = nverts(p)
    zero = p["mat"] == "zero"
    pts = [(0, 0)] * V if zero else [(rnd.randint(0, G), rnd.randint(0, G)) for _ in range(V)]

    def d(a, b):  # khoảng cách làm tròn lên, tối thiểu 1 (trừ ma trận 0)
        return 0 if zero else max(1, math.ceil(math.hypot(pts[a][0] - pts[b][0], pts[a][1] - pts[b][1])))

    def near_depot(v):  # thời gian tới v từ một depot ngẫu nhiên (để cửa sổ chặt vẫn khả thi)
        return d(rnd.randrange(K), v)

    def window(mode, v):
        if mode == "normal":
            e = rnd.randint(0, H); return e, e + rnd.randint(5, 35)
        if mode == "wide":
            return rnd.randint(0, H), 10 ** 5
        if mode == "tight":
            e = near_depot(v) + rnd.randint(0, max(1, H // 5)); return e, e + rnd.randint(0, 2)
        if mode == "point":
            e = near_depot(v) + rnd.randint(0, 10); return e, e
        return 0, 0  # impossible

    lo_s, hi_s = p["S"]; rev_lo, rev_hi = p["rev"]
    rows_p, rows_h, sumrev = [], [], 0
    for i in range(N):
        a = K + 2 * i
        e, l = window(p["win"], a); s = rnd.randint(lo_s, hi_s); t = rnd.randint(rev_lo, rev_hi); sumrev += t
        rows_p.append("%d %d %d %d %d %d" % (a + 1, a + 2, e, l, s, t))
    for j in range(M):
        a = K + 2 * N + 2 * j; b = a + 1
        ep, lp = window(p["win"], a)
        s = rnd.randint(lo_s, hi_s); t = rnd.randint(rev_lo, rev_hi); sumrev += t
        w = rnd.randint(*p["w"])
        mode = p["win"]
        if mode == "normal":
            ed = lp + d(a, b) + rnd.randint(0, 40); ld = ed + rnd.randint(10, 70)
        elif mode == "wide":
            ed, ld = rnd.randint(0, H), 10 ** 5
        elif mode == "tight":
            ed = ep + s + d(a, b) + rnd.randint(0, 3); ld = ed + rnd.randint(0, 2)
        elif mode == "point":
            ed = ep + s + d(a, b) + rnd.randint(0, 10); ld = ed
        else:
            ed = ld = 0
        rows_h.append("%d %d %d %d %d %d %d %d %d" % (a + 1, b + 1, w, ep, lp, ed, ld, s, t))
    dep = ["%d %d" % (k + 1, rnd.randint(*p["Q"])) for k in range(K)]
    T, C = [], []
    for u in range(V):
        xu, yu = pts[u]
        if p["mat"] == "euclid" or zero:
            tr = [0 if (u == v or zero) else max(1, math.ceil(math.hypot(xu - pts[v][0], yu - pts[v][1]))) for v in range(V)]
            cr = [int(2.5 * x + 0.5) for x in tr]
        else:  # asym
            tr = [0 if u == v else max(1, d(u, v) + rnd.randint(-10, 10)) for v in range(V)]
            cr = [0 if u == v else rnd.randint(2, 300) for v in range(V)]
        T.append(tr); C.append(cr)
    out = ["%d %d %d" % (K, N, M)] + dep + rows_p + rows_h
    out += [" ".join(map(str, r)) for r in T] + [" ".join(map(str, r)) for r in C]
    exp = p["expect"]
    if exp == "sumrev":
        exp = sumrev
    meta = dict(name=name, K=K, N=N, M=M, V=V, expect=exp, note=p["note"], big=V > 600)
    return "\n".join(out) + "\n", meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
    ap.add_argument("--seed", default="2026")
    ap.add_argument("--only", default="")
    ap.add_argument("--skip-big", action="store_true")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    for name, p in SC.items():
        if a.only and a.only not in name:
            continue
        if a.skip_big and nverts(p) > 600:
            continue
        if a.list:
            print("%-16s K=%-3d N=%-3d M=%-3d V=%-5d %s" % (name, p["K"], p["N"], p["M"], nverts(p), p["note"])); continue
        text, meta = make(name, p, a.seed)
        with open(os.path.join(a.out, name + ".txt"), "w") as f:
            f.write(text)
        with open(os.path.join(a.out, name + ".json"), "w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False)
        print("%-16s V=%-5d %6.1f MB  %s" % (name, meta["V"], len(text) / 2 ** 20, p["note"]))


if __name__ == "__main__":
    main()
