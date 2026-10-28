import itertools
import math
import os
import random
import sys
import time
from bisect import bisect_left
INF = float('inf')
sys.setrecursionlimit(20000)
EPS = 1e-07
TIME_LIMIT = float(os.environ.get('SOICT_TL', 270.0))
POLISH = 8.0
HARD = 290.0
BIG_POOL = 40000
SHRINK = 0.16
MAX_ROUTES = 260000
STAT = {'it': 0}
SORT_CAND = os.environ.get('SOICT_SORT', '1') != '0'
SYM = os.environ.get('SOICT_SYM', '1') != '0'
COMPRESS = os.environ.get('SOICT_COMPRESS', '1') != '0'
PRM = dict(T0=0.12, T1=0.004, qf=0.3, qcap=14, U=8, p_worst=4.0, p_shaw=3.0, reset=4000, seg=60, rho=0.25, noise=0.0)

class Inst(object):

    def __init__(s, text):
        lines = [l.split('#')[0].strip() for l in text.splitlines()]
        x = list(map(float, ' '.join((l for l in lines if l)).split()))
        K, N, M = (int(x[0]), int(x[1]), int(x[2]))
        V = 2 * N + 2 * M + K
        s.K, s.N, s.M, s.V, s.R = (K, N, M, V, N + M)
        pos = 3
        s.depot, s.Q = ([], [])
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
        s.P, s.D, s.rev, s.w, s.typ = ([], [], [], [], [])
        for _ in range(N):
            p, d = (int(x[pos]) - 1, int(x[pos + 1]) - 1)
            e, l, sv, t = x[pos + 2:pos + 6]
            pos += 6
            r = len(s.P)
            s.P.append(p)
            s.D.append(d)
            s.rev.append(t)
            s.w.append(0.0)
            s.typ.append(0)
            s.E[p], s.L[p], s.S[p], s.tp[p], s.req[p] = (e, l, sv, 1, r)
            s.E[d], s.L[d], s.S[d], s.tp[d], s.req[d] = (0.0, INF, sv, 2, r)
        for _ in range(M):
            p, d = (int(x[pos]) - 1, int(x[pos + 1]) - 1)
            w, ep, lp, ed, ld, sv, t = x[pos + 2:pos + 9]
            pos += 9
            r = len(s.P)
            s.P.append(p)
            s.D.append(d)
            s.rev.append(t)
            s.w.append(w)
            s.typ.append(1)
            s.E[p], s.L[p], s.S[p], s.W[p], s.tp[p], s.req[p] = (ep, lp, sv, w, 3, r)
            s.E[d], s.L[d], s.S[d], s.W[d], s.tp[d], s.req[d] = (ed, ld, sv, -w, 4, r)
        s.T = [x[pos + i * V:pos + (i + 1) * V] for i in range(V)]
        pos += V * V
        s.C = [x[pos + i * V:pos + (i + 1) * V] for i in range(V)]

class State(object):

    def __init__(s, ins):
        s.ins = ins
        s.routes = [[] for _ in range(ins.K)]
        s.info = [s.evaluate(k, []) for k in range(ins.K)]
        s.where = [-1] * ins.R
        s.revsum = 0.0
        s.ver = list(range(ins.K))
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
        I = s.ins
        T, C, E, L, S, W = (I.T, I.C, I.E, I.L, I.S, I.W)
        nodes = [I.depot[k]] + stops
        n = len(nodes)
        cap = I.Q[k] + 1e-09
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
        return s.revsum - sum((f[4] for f in s.info))

    def scan(s, r, k):
        I = s.ins
        T, C, E, L, S, tp = (I.T, I.C, I.E, I.L, I.S, I.tp)
        nodes, dep, ld, lat, _ = s.info[k]
        n = len(nodes)
        p, d, w = (I.P[r], I.D[r], I.w[r])
        cap = I.Q[k] + 1e-09
        Lp, Ep, Sp = (L[p], E[p], S[p])
        Ld, Ed, Sd = (L[d], E[d], S[d])
        Tp, Cp, Cd = (T[p], C[p], C[d])
        parcel = I.typ[r] == 1
        best = INF
        bi = bj = -1
        for i in range(n):
            a = nodes[i]
            if tp[a] == 1:
                continue
            ap = dep[i] + T[a][p]
            if ap > Lp or ld[i] + w > cap:
                continue
            t = (ap if ap >= Ep else Ep) + Sp
            ca = C[a][p]
            ad = t + Tp[d]
            if ad <= Ld:
                td = (ad if ad >= Ed else Ed) + Sd
                if i + 1 < n:
                    b = nodes[i + 1]
                    if td + T[d][b] <= lat[i + 1]:
                        dc = ca + Cp[d] + Cd[b] - C[a][b]
                        if dc < best:
                            best, bi, bj = (dc, i, i)
                else:
                    dc = ca + Cp[d]
                    if dc < best:
                        best, bi, bj = (dc, i, i)
            if not parcel or i + 1 >= n:
                continue
            s1 = nodes[i + 1]
            cpick = ca + Cp[s1] - C[a][s1]
            cur, tc = (p, t)
            for m in range(i + 1, n):
                v = nodes[m]
                arr = tc + T[cur][v]
                if arr > L[v] or ld[m] + w > cap:
                    break
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
                            best, bi, bj = (dc, i, m)
                else:
                    dc = cpick + C[v][d]
                    if dc < best:
                        best, bi, bj = (dc, i, m)
        if bi < 0:
            return None
        return (best, bi, bj)

    def best_insert(s, r, ks=None):
        best = None
        for k in range(s.ins.K) if ks is None else ks:
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
        p, d = (I.P[r], I.D[r])
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

def greedy(st, deadline):
    I = st.ins
    R, K = (I.R, I.K)
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

def add_unserved(st, r):
    x = st.best_insert(r)
    if x is not None and st.ins.rev[r] - x[0] > EPS:
        return st.insert(r, x[1], x[2], x[3])
    return False

def relocate(st, r):
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
        return True
    st.restore(sn)
    return False

def swap(st, r1, r2):
    a, b = (st.where[r1], st.where[r2])
    base = st.benefit()
    sn = st.snap({a, b})
    if st.remove(r1) and st.remove(r2):
        x = st.scan(r1, b)
        if x is not None and st.insert(r1, b, x[1], x[2]):
            y = st.scan(r2, a)
            if y is not None and st.insert(r2, a, y[1], y[2]) and (st.benefit() > base + EPS):
                return True
    st.restore(sn)
    return False

def replace(st, ro, ri):
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

def _pick(cand, q, rng, p):
    out = []
    while len(out) < q and cand:
        out.append(cand.pop(int(len(cand) * rng.random() ** p))[1])
    return out

def d_random(st, q, rng, sv, un):
    rs = rng.sample(sv, min(q, len(sv)))
    return (rs, []) if st.remove_many(rs) else None

def d_worst(st, q, rng, sv, un):
    I = st.ins
    C, tp = (I.C, I.tp)
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
    cand = sorted(((I.rev[r] - x, r) for r, x in sav.items()))
    rs = _pick(cand, q, rng, PRM['p_worst'])
    return (rs, []) if st.remove_many(rs) else None

def d_shaw(st, q, rng, sv, un, from_unserved):
    I = st.ins
    T, E, P, D = (I.T, I.E, I.P, I.D)
    if from_unserved and un:
        seed, extra = (rng.choice(un), True)
    else:
        seed, extra = (rng.choice(sv), False)
    ps, ds = (P[seed], D[seed])
    es = E[ps]
    inv_t, inv_s = (0.5 / I.avgT, 1.0 / I.tsc)
    cand = sorted((((T[ps][P[r]] + T[ds][D[r]]) * inv_t + abs(es - E[P[r]]) * inv_s, r) for r in sv if r != seed))
    rs = _pick(cand, q - (0 if extra else 1), rng, PRM['p_shaw'])
    if not extra:
        rs.insert(0, seed)
    if not st.remove_many(rs):
        return None
    return (rs, [seed] if extra else [])

def r_greedy(st, pool, rng):
    I = st.ins
    K, rev, nz = (I.K, I.rev, PRM['noise'])
    cand = {r: [st.scan_c(r, k) for k in range(K)] for r in pool}
    while cand:
        best = None
        for r, row in cand.items():
            bx = None
            for k in range(K):
                x = row[k]
                if x is not None and (bx is None or x[0] < bx[0]):
                    bx, bk = (x, k)
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
    I = st.ins
    K, rev = (I.K, I.rev)
    cand = {r: [st.scan_c(r, k) for k in range(K)] for r in pool}
    while cand:
        best = None
        for r, row in cand.items():
            gs = sorted(((rev[r] - x[0], k) for k, x in enumerate(row) if x is not None), reverse=True)
            if not gs or gs[0][0] <= EPS:
                continue
            g1 = gs[0][0]
            reg = sum((g1 - gs[i][0] for i in range(1, min(m, len(gs))))) + 1000000.0 * max(0, m - len(gs))
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
    I = st.ins
    R, K, V = (I.R, I.K, I.V)
    if R == 0:
        return
    I.avgT = max(1.0, sum(map(sum, I.T)) / (V * V))
    I.tsc = max([1.0] + [x for x in I.L if x < INF])
    avg_rev = sum(I.rev) / R
    T0, T1 = (PRM['T0'] * avg_rev, PRM['T1'] * avg_rev)
    destroys = [d_random, d_worst, lambda *a: d_shaw(*a, False), lambda *a: d_shaw(*a, True)]
    repairs = [r_greedy, lambda *a: r_regret(*a, 2), lambda *a: r_regret(*a, 3)]
    wd, wr = ([1.0] * len(destroys), [1.0] * len(repairs))
    sd, sr = ([0.0] * len(destroys), [0.0] * len(repairs))
    nd, nr = ([0] * len(destroys), [0] * len(repairs))
    cur = best = st.benefit()
    best_sn = st.snap(range(K))
    t_start = time.time()
    span = max(1e-09, deadline - t_start)
    it = last_best = 0
    while True:
        now = time.time()
        if now >= deadline or it - last_best > 200000:
            break
        it += 1
        temp = T0 * (T1 / T0) ** ((now - t_start) / span)
        sv = [r for r in range(R) if st.where[r] >= 0]
        un = [r for r in range(R) if st.where[r] < 0]
        di, ri = (_roulette(wd, rng), _roulette(wr, rng))
        sn = st.snap(range(K))
        removed, extra = ([], [])
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
        sd[di] += sc
        sr[ri] += sc
        nd[di] += 1
        nr[ri] += 1
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

def vehicle_groups(I):
    if not SYM:
        return list(range(I.K))
    rv = [v for v in range(I.V) if I.tp[v] != 0]
    seen, grp = ({}, [])
    for k in range(I.K):
        o = I.depot[k]
        key = (I.Q[k], tuple((I.T[o][v] for v in rv)), tuple((I.C[o][v] for v in rv)))
        grp.append(seen.setdefault(key, k))
    return grp

def alive_requests(I):
    if not COMPRESS:
        return list(range(I.R))
    V, T, L = (I.V, I.T, I.L)
    a = [INF] * V
    for u in I.depot:
        a[u] = 0.0
    done = [False] * V
    for _ in range(V):
        u, best = (-1, INF)
        for v in range(V):
            if not done[v] and a[v] < best:
                u, best = (v, a[v])
        if u < 0:
            break
        done[u] = True
        Tu = T[u]
        for v in range(V):
            x = best + Tu[v]
            if x < a[v]:
                a[v] = x
    I.amin = a
    qmax = max(I.Q) + 1e-09 if I.Q else 0.0
    alive = []
    for r in range(I.R):
        p, d = (I.P[r], I.D[r])
        if a[p] > L[p] + EPS or a[d] > L[d] + EPS or I.w[r] > qmax:
            continue
        alive.append(r)
    return alive

def compact_pools(pools):
    used = 0
    for pk in pools:
        for z in pk:
            used |= z[1]
    newid = {}
    x = used
    while x:
        low = x & -x
        newid[low.bit_length() - 1] = len(newid)
        x ^= low
    if not COMPRESS or len(newid) == used.bit_length():
        return pools
    out = []
    memo = {}
    for pk in pools:
        if id(pk) in memo:
            out.append(memo[id(pk)])
            continue
        row = []
        for pf, mk, nd in pk:
            m = 0
            x = mk
            while x:
                low = x & -x
                m |= 1 << newid[low.bit_length() - 1]
                x ^= low
            row.append((pf, m, nd))
        memo[id(pk)] = row
        out.append(row)
    return out

def metric_ok(I):
    sv = [I.S[v] for v in range(I.V) if I.tp[v] != 0]
    if not sv:
        return False
    rng = random.Random(1)
    V, T = (I.V, I.T)
    worst = 0.0
    for _ in range(30000):
        u, v, w = (rng.randrange(V), rng.randrange(V), rng.randrange(V))
        x = T[u][v] - T[u][w] - T[w][v]
        if x > worst:
            worst = x
    return worst <= min(sv)

def build_pool(I, deadline, max_states=6000000, maxreq=99, alive=None):
    T, C, E, L, S = (I.T, I.C, I.E, I.L, I.S)
    if alive is None:
        alive = list(range(I.R))
    P, D = ([I.P[r] for r in alive], [I.D[r] for r in alive])
    rev, w, typ = ([I.rev[r] for r in alive], [I.w[r] for r in alive], [I.typ[r] for r in alive])
    R = len(alive)
    pools = []
    states = [0]
    nroute = [0]
    bad = [False]
    metric = metric_ok(I)
    LP = []
    for c in range(R):
        l = L[P[c]]
        if typ[c] == 1 and metric:
            l2 = L[D[c]] - S[P[c]] - T[P[c]][D[c]]
            if E[P[c]] > l2:
                l = -1.0
            elif l2 < l:
                l = l2
        LP.append(l)
    amin = getattr(I, 'amin', None) or [0.0] * I.V
    dl = [max(amin[u], E[u]) + S[u] if I.tp[u] != 0 else 0.0 for u in range(I.V)]
    order = sorted(range(R), key=lambda r: LP[r]) if SORT_CAND else list(range(R))
    cand = [[r for r in order if dl[u] + T[u][P[r]] <= LP[r]] for u in range(I.V)]
    candL = [[LP[r] for r in cl] for cl in cand]
    grp = vehicle_groups(I)
    for k in range(I.K):
        if grp[k] != k:
            pools.append(pools[grp[k]])
            continue
        Q = I.Q[k] + 1e-09
        best = {}
        path = []

        def dfs(cur, t, load, carried, used, rv, cs, nr):
            states[0] += 1
            if states[0] > max_states or (states[0] & 4095 == 0 and time.time() > deadline):
                bad[0] = True
                return
            if path and (not carried) and (rv - cs > 1e-09):
                o = best.get(used)
                if o is None or rv - cs > o[0] + 1e-09:
                    if o is None:
                        nroute[0] += 1
                        if nroute[0] > MAX_ROUTES:
                            bad[0] = True
                            return
                    best[used] = (rv - cs, list(path))
            for r in (cand[cur][bisect_left(candL[cur], t):] if SORT_CAND else cand[cur]) if nr < maxreq else ():
                if used >> r & 1:
                    continue
                p = P[r]
                a = t + T[cur][p]
                if a > LP[r]:
                    continue
                t1 = (a if a >= E[p] else E[p]) + S[p]
                if typ[r] == 0:
                    d = D[r]
                    path.append(p)
                    path.append(d)
                    dfs(d, t1 + T[p][d] + S[d], load, carried, used | 1 << r, rv + rev[r], cs + C[cur][p] + C[p][d], nr + 1)
                    path.pop()
                    path.pop()
                elif load + w[r] <= Q:
                    path.append(p)
                    dfs(p, t1, load + w[r], carried | 1 << r, used | 1 << r, rv + rev[r], cs + C[cur][p], nr + 1)
                    path.pop()
                if bad[0]:
                    return
            c = carried
            while c:
                low = c & -c
                r = low.bit_length() - 1
                c ^= low
                d = D[r]
                a = t + T[cur][d]
                if a > L[d]:
                    continue
                path.append(d)
                dfs(d, (a if a >= E[d] else E[d]) + S[d], load - w[r], carried & ~low, used, rv, cs + C[cur][d], nr)
                path.pop()
                if bad[0]:
                    return
        dfs(I.depot[k], 0.0, 0.0, 0, 0, 0.0, 0.0, 0)
        if bad[0]:
            return None
        pools.append(sorted(((pf, mk, nd) for mk, (pf, nd) in best.items()), key=lambda z: -z[0]))
    return pools

def bnb(pools, rem, used, base, node_limit, deadline, grp=None):
    if grp is None:
        grp = list(range(len(pools)))
    best = [base]
    bsel = [None]
    sel = []
    nodes = [0]
    stop = [False]
    lo = [0] * len(pools)

    def rec(rem, used, cur):
        nodes[0] += 1
        if nodes[0] > node_limit or (nodes[0] & 255 == 0 and time.time() > deadline):
            stop[0] = True
            return
        if cur > best[0] + 1e-09:
            best[0] = cur
            bsel[0] = list(sel)
        first, cnt = ({}, {})
        for k in rem:
            g = grp[k]
            cnt[g] = cnt.get(g, 0) + 1
            if g not in first or k < first[g]:
                first[g] = k
        ub = 0.0
        bk = {}
        for g, f in first.items():
            n, c, pl = (cnt[g], 0, pools[f])
            for i in range(lo[g], len(pl)):
                z = pl[i]
                if not z[1] & used:
                    if c == 0:
                        bk[f] = z
                    ub += z[0]
                    c += 1
                    if c == n:
                        break
        if not bk or cur + ub <= best[0] + 1e-09:
            return
        kk = max(bk, key=lambda k: bk[k][0])
        others = ub - bk[kk][0]
        g = grp[kk]
        pl = pools[kk]
        rem2 = rem - {kk}
        old = lo[g]
        for i in range(old, len(pl)):
            z = pl[i]
            if z[1] & used:
                continue
            if cur + z[0] + others <= best[0] + 1e-09:
                break
            sel.append((kk, z))
            lo[g] = i + 1
            rec(rem2, used | z[1], cur + z[0])
            sel.pop()
            lo[g] = old
            if stop[0]:
                return
        rec(rem - {k for k in rem if grp[k] == g}, used, cur)
    rec(frozenset(rem), used, 0.0)
    return ((best[0], bsel[0]) if bsel[0] is not None else None, stop[0], nodes[0])

def lns_routes(pools, chosen, deadline, rng, on_better, size=6, node_limit=30000, grp=None):
    K = len(pools)
    while time.time() < deadline:
        sub = rng.sample(range(K), min(size, K))
        subset = set(sub)
        used = 0
        for k in range(K):
            if k not in subset and chosen[k]:
                used |= chosen[k][1]
        base = sum((chosen[k][0] for k in sub if chosen[k]))
        res, hit, nd = bnb(pools, subset, used, base, node_limit, deadline, grp)
        if res is not None:
            for k in sub:
                chosen[k] = None
            for k, z in res[1]:
                chosen[k] = z
            on_better()
        if hit:
            if rng.random() < 0.3:
                size = max(4, size - 1)
        elif nd < node_limit // 10 and rng.random() < 0.3:
            size = min(K, size + 1)

def lagrange(R, pools, lb, deadline, iters=1500):
    K = len(pools)
    reqs = []
    for k in range(K):
        row = []
        for z in pools[k]:
            rs = []
            x = z[1]
            while x:
                low = x & -x
                rs.append(low.bit_length() - 1)
                x ^= low
            row.append(rs)
        reqs.append(row)
    lam = [0.0] * R
    bub, blam, theta, stall = (float('inf'), lam[:], 2.0, 0)
    for _ in range(iters):
        if time.time() > deadline:
            break
        ub = sum(lam)
        cover = [0] * R
        for k in range(K):
            bv, bi = (0.0, -1)
            for i, z in enumerate(pools[k]):
                v = z[0]
                for r in reqs[k][i]:
                    v -= lam[r]
                if v > bv:
                    bv, bi = (v, i)
            ub += bv
            if bi >= 0:
                for r in reqs[k][bi]:
                    cover[r] += 1
        if ub < bub - 1e-09:
            bub, blam, stall = (ub, lam[:], 0)
        else:
            stall += 1
            if stall >= 10:
                theta *= 0.6
                stall = 0
        g = [1 - c for c in cover]
        nrm = sum((x * x for x in g))
        if nrm == 0 or theta * (bub - lb) <= 1e-09 * nrm:
            break
        step = theta * (bub - lb) / nrm
        lam = [max(0.0, l - step * x) for l, x in zip(lam, g)]
    return (bub, blam, reqs)

def fix_pools(pools, reqs, lam, ub, lb):
    out = []
    for k in range(len(pools)):
        rp = [z[0] - sum((lam[r] for r in rs)) for z, rs in zip(pools[k], reqs[k])]
        bk = max([0.0] + rp)
        out.append([z for z, v in zip(pools[k], rp) if ub - bk + v >= lb - 1e-09])
    return out

def dominance_filter(pools):
    out = []
    for pk in pools:
        best = {z[1]: z[0] for z in pk}
        keep = []
        for z in pk:
            bs = []
            x = z[1]
            while x:
                low = x & -x
                bs.append(low)
                x ^= low
            dom = False
            for r in range(1, len(bs)):
                for comb in itertools.combinations(bs, r):
                    sub = 0
                    for b in comb:
                        sub |= b
                    v = best.get(sub)
                    if v is not None and v >= z[0] - 1e-09:
                        dom = True
                        break
                if dom:
                    break
            if not dom:
                keep.append(z)
        out.append(keep)
    return out

def shrink_pools(I, pools, deadline, rng, hold):
    K = I.K
    pools = dominance_filter(pools)
    Rc = max([0] + [z[1].bit_length() for pk in pools for z in pk])
    grp = vehicle_groups(I)
    chosen = [None] * K

    def total():
        return sum((z[0] for z in chosen if z))

    def save():
        hold(total(), [list(z[2]) if z else [] for z in chosen])
    now = time.time()
    lns_routes(pools, chosen, now + 0.08 * (deadline - now), rng, save, grp=grp)
    lb = total()
    now = time.time()
    ub, lam, reqs = lagrange(Rc, pools, lb, now + 0.17 * (deadline - now))
    delta = SHRINK * lb / max(1, K)
    out = []
    for k in range(K):
        rp = [z[0] - sum((lam[r] for r in reqs[k][i])) for i, z in enumerate(pools[k])]
        bk = max([0.0] + rp)
        out.append([z for z, v in zip(pools[k], rp) if v >= bk - delta])
    return out

def exact_solve(I, pools, deadline, rng, hold):
    K = I.K
    allk = set(range(K))
    chosen = [None] * K
    grp = vehicle_groups(I)
    Rc = max([0] + [z[1].bit_length() for pk in pools for z in pk])

    def total():
        return sum((z[0] for z in chosen if z))

    def save():
        hold(total(), [list(z[2]) if z else [] for z in chosen])

    def adopt(res):
        chosen[:] = [None] * K
        for k, z in res[1]:
            chosen[k] = z
        save()
    now = time.time()
    res, cut, _ = bnb(pools, allk, 0, 0.0, 10 ** 12, now + min(10.0, 0.05 * (deadline - now)), grp)
    if res is not None:
        adopt(res)
    if not cut:
        return
    cur, chunk, lam = (pools, 6.0, None)
    while time.time() < deadline:
        lns_routes(cur, chosen, min(deadline, time.time() + chunk), rng, save, grp=grp)
        lb = total()
        if lam is None:
            now = time.time()
            ub, lam, reqs = lagrange(Rc, pools, lb, now + 0.15 * (deadline - now))
        cur = fix_pools(pools, reqs, lam, ub, lb)
        res, cut, _ = bnb(cur, allk, 0, lb - 1e-06, 10 ** 12, min(deadline, time.time() + chunk), grp)
        if res is not None and res[0] > lb + 1e-09:
            adopt(res)
        if not cut:
            return
        chunk = min(chunk * 1.5, 60.0)

def verify(I, routes):
    seen = set()
    total = 0.0
    for k, stops in enumerate(routes):
        u, t, l = (I.depot[k], 0.0, 0.0)
        pend = set()
        n = len(stops)
        for i, v in enumerate(stops):
            if v in seen or I.tp[v] == 0:
                return None
            seen.add(v)
            a = t + I.T[u][v]
            if a > I.L[v]:
                return None
            tv, r = (I.tp[v], I.req[v])
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
            if l > I.Q[k] + 1e-09:
                return None
            t = (a if a >= I.E[v] else I.E[v]) + I.S[v]
            total -= I.C[u][v]
            u = v
        if pend:
            return None
    return total

def fmt(x):
    return str(int(round(x))) if abs(x - round(x)) < 1e-09 else '%.6f' % x
HOLD = {'routes': None, 'safe': None, 'val': 0.0}
DONE = [False]

def record(st):
    HOLD['routes'] = list(st.routes)

def finish(I, outfile):
    if DONE[0]:
        return
    DONE[0] = True
    val, routes = (0.0, [[] for _ in range(I.K)])
    for cand in (HOLD['routes'], HOLD['safe']):
        if cand is not None:
            try:
                v = verify(I, cand)
            except Exception:
                v = None
            if v is not None:
                val, routes = (v, cand)
                break
    out = [fmt(val)] + [' '.join([str(len(r))] + [str(v + 1) for v in r]) for r in routes]
    res = '\n'.join(out) + '\n'
    if outfile:
        with open(outfile, 'w') as f:
            f.write(res)
    else:
        sys.stdout.write(res)
        sys.stdout.flush()

def hold_better(val, routes):
    if val > HOLD['val'] + EPS:
        HOLD['val'] = val
        HOLD['routes'] = routes

def solve(I, t0):
    rng = random.Random(12345)
    st = State(I)
    deadline = t0 + TIME_LIMIT
    greedy(st, deadline)
    HOLD['safe'] = list(st.routes)
    HOLD['val'] = verify(I, HOLD['safe']) or 0.0
    record(st)
    try:
        local_search(st, deadline, rng)
        record(st)
        HOLD['val'] = verify(I, HOLD['routes']) or HOLD['val']
        pools = None
        alive = alive_requests(I)
        for frac, mr in ((0.1, 99), (0.16, 4), (0.12, 3)):
            pools = build_pool(I, min(deadline, time.time() + frac * TIME_LIMIT), 6000000 if mr == 99 else 30000000, mr, alive)
            if pools is not None:
                pools = compact_pools(pools)
                break
        if pools is not None:
            if sum((len(p) for p in pools)) > BIG_POOL:
                try:
                    pools = shrink_pools(I, pools, deadline, rng, hold_better)
                except Exception:
                    pass
            exact_solve(I, pools, deadline, rng, hold_better)
            return
        alns(st, deadline, rng, record)
        local_search(st, deadline + min(POLISH, 0.04 * TIME_LIMIT), rng)
        if st.benefit() >= (verify(I, HOLD['routes']) or -INF) - EPS:
            record(st)
    except Exception:
        pass

def arm_watchdog(I, outfile, t0):
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
