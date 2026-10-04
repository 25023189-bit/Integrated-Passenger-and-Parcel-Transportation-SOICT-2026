"""Chạy toàn bộ bộ test sinh ra: checker + điểm + thời gian + RAM đỉnh -> bảng report.md / results.csv / results.json.
Ví dụ:
  python run_suite.py --tl 20                  # nhanh: mỗi test tối đa ~20 s
  python run_suite.py --full --only big        # đúng giới hạn thật của solution (250 s) cho các test chứa 'big'
  python run_suite.py --tl 20 --mem-limit 256 --time-limit 300"""
import argparse, csv, json, os, sys, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness

ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solution", default=os.path.join(ROOT, "Code python", "solution.py"))
    ap.add_argument("--tests", default=os.path.join(HERE, "tests"))
    ap.add_argument("--tl", type=float, default=20, help="SOICT_TL (giây) truyền cho solution")
    ap.add_argument("--full", action="store_true", help="không đặt SOICT_TL: dùng giới hạn mặc định của solution")
    ap.add_argument("--only", default="", help="chỉ chạy test có tên chứa chuỗi này")
    ap.add_argument("--skip-big", action="store_true")
    ap.add_argument("--time-limit", type=float, default=300.0, help="giới hạn thời gian của máy chấm (s)")
    ap.add_argument("--mem-limit", type=float, default=0.0, help="giới hạn RAM máy chấm (MB); 0 = chưa biết")
    ap.add_argument("--out", default=os.path.join(HERE, "report"))
    ap.add_argument("--python", default=None)
    a = ap.parse_args()
    if not os.path.isfile(a.solution):
        sys.exit("Không thấy solution: %s (dùng --solution)" % a.solution)
    if not os.path.isdir(a.tests) or not any(f.endswith(".txt") for f in os.listdir(a.tests)):
        sys.exit("Chưa có test: chạy `python gen_tests.py` trước.")
    os.makedirs(a.out, exist_ok=True)
    jpath = os.path.join(a.out, "results.json")
    prev = {}
    if os.path.exists(jpath):
        try:
            prev = {r["name"]: r for r in json.load(open(jpath, encoding="utf-8"))}
        except Exception:
            pass
    metas = []
    for f in sorted(os.listdir(a.tests)):
        if f.endswith(".json"):
            m = json.load(open(os.path.join(a.tests, f), encoding="utf-8"))
            if (a.only in m["name"]) and not (a.skip_big and m["big"]):
                metas.append(m)
    metas.sort(key=lambda m: m["V"])
    rows = []
    tl = None if a.full else a.tl
    print("Chạy %d test, TL=%s, solution=%s" % (len(metas), "mặc định" if a.full else tl, a.solution))
    for m in metas:
        inp = os.path.join(a.tests, m["name"] + ".txt")
        out = os.path.join(a.out, m["name"] + ".out")
        r = harness.run_and_check(a.solution, inp, out, tl, timeout=a.time_limit + 30, py=a.python)
        st, note = "OK", ""
        if r["timeout"] or r["time"] > a.time_limit:
            st = "TLE"
        elif r["rc"] != 0:
            st = "RE"
        elif r["score"] is None:
            st, note = "WA", r["msg"]
        elif m["expect"] is not None and abs(r["score"] - m["expect"]) > 1e-6:
            st, note = "SAI_ĐÁP_ÁN", "kỳ vọng %s, được %s" % (m["expect"], r["score"])
        if st == "OK" and a.mem_limit and r["mem"] and r["mem"] > a.mem_limit:
            st = "MLE"
        if st in ("RE", "TLE"):
            note = r["msg"]
        old = prev.get(m["name"], {}).get("score")
        if st == "OK" and old is not None and r["score"] < old - 1e-9:
            note = (note + " ").lstrip() + "⚠ giảm so với lần trước (%s)" % old
        row = dict(name=m["name"], K=m["K"], N=m["N"], M=m["M"], V=m["V"], score=r["score"], time=round(r["time"], 2),
                   mem=None if r["mem"] is None else round(r["mem"], 1), status=st, note=note or m["note"])
        rows.append(row)
        print("%-16s V=%-5d %-10s điểm=%-10s %7.1fs %8s MB  %s" % (row["name"], row["V"], st, row["score"], row["time"], row["mem"], note))
    json.dump(rows, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    with open(os.path.join(a.out, "results.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
    write_md(a, rows, tl)


def write_md(a, rows, tl):
    bad = [r for r in rows if r["status"] != "OK"]
    mems = [r for r in rows if r["mem"] is not None]
    L = ["# Báo cáo bộ test cực đoan + test lớn", "",
         "- Thời điểm: %s | Solution: `%s` | SOICT_TL: %s" % (time.strftime("%Y-%m-%d %H:%M"), os.path.basename(os.path.dirname(a.solution)) + "/" + os.path.basename(a.solution), "mặc định" if tl is None else "%g s" % tl),
         "- Số test: %d | OK: %d | Lỗi: %d" % (len(rows), len(rows) - len(bad), len(bad)), ""]
    if mems:
        mx = max(mems, key=lambda r: r["mem"])
        L.append("- RAM đỉnh lớn nhất: **%.1f MB** (test `%s`, V=%d)" % (mx["mem"], mx["name"], mx["V"]))
        for lim in (256, 512, 1024):
            L.append("  - %d test vượt %d MB" % (sum(1 for r in mems if r["mem"] > lim), lim))
    tx = max(rows, key=lambda r: r["time"])
    L += ["- Thời gian lớn nhất: **%.1f s** (test `%s`)" % (tx["time"], tx["name"]), ""]
    L += ["| Test | K | N | M | V | Điểm | Thời gian (s) | RAM đỉnh (MB) | Trạng thái | Ghi chú |", "|---|--:|--:|--:|--:|--:|--:|--:|:-:|---|"]
    for r in rows:
        L.append("| %s | %d | %d | %d | %d | %s | %.2f | %s | %s | %s |" % (
            r["name"], r["K"], r["N"], r["M"], r["V"], "—" if r["score"] is None else ("%g" % r["score"]), r["time"],
            "n/a" if r["mem"] is None else "%.1f" % r["mem"], r["status"] if r["status"] == "OK" else "**%s**" % r["status"], r["note"]))
    L += ["", "> Lưu ý: ở TL ngắn, RAM thật có thể bị đánh giá thấp vì ALNS/exact_solve (`build_pool` tới 6.000.000 trạng thái) còn chạy tiếp. Chạy `--full --only big` ít nhất một lần để lấy RAM đỉnh thật."]
    open(os.path.join(a.out, "report.md"), "w", encoding="utf-8").write("\n".join(L) + "\n")
    print("\nĐã ghi %s" % os.path.join(a.out, "report.md"))


if __name__ == "__main__":
    main()
