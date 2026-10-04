import sys
"""Bộ hồi quy bất biến: chạy 8 test thật, so với bảng điểm chuẩn trong baseline.json, báo ĐỎ nếu lệch.
  python regression.py                 # chạy cả 8 test, so với chuẩn (tổng chuẩn = 27738)
  python regression.py --record        # ghi điểm từng test làm chuẩn (chỉ khi tổng đúng 27738; --force để bỏ qua)
  python regression.py --only 3,5,6    # chạy nhanh vài test (không so tổng)
  python regression.py --tl 60         # đổi giới hạn thời gian (phải trùng với TL lúc --record)
Mã thoát 0 = xanh, 1 = có lệch/lỗi (dùng được trong git hook hoặc CI)."""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import harness

ROOT = os.path.dirname(HERE)
os.system("")  # bật mã màu ANSI trên Windows 10+
RED, GRN, YEL, END = "\033[1;31m", "\033[1;32m", "\033[1;33m", "\033[0m"


def paint(c, s):
    return c + s + END


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solution", default=os.path.join(ROOT, "Code python", "solution.py"))
    ap.add_argument("--tests", default=os.path.join(ROOT, "Test Case"))
    ap.add_argument("--baseline", default=os.path.join(HERE, "baseline.json"))
    ap.add_argument("--tl", type=float, default=None, help="mặc định: lấy từ baseline (null = giới hạn mặc định của solution)")
    ap.add_argument("--full", action="store_true", help="bỏ SOICT_TL (giới hạn mặc định của solution)")
    ap.add_argument("--only", default="", help="danh sách số test, ví dụ 3,5,6")
    ap.add_argument("--record", action="store_true")
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--allow-up", action="store_true", help="điểm cao hơn chuẩn chỉ cảnh báo vàng, không tính là lỗi")
    ap.add_argument("--python", default=None)
    a = ap.parse_args()
    if not os.path.isfile(a.solution):
        sys.exit("Không thấy solution: %s" % a.solution)
    base = json.load(open(a.baseline, encoding="utf-8"))
    tl = None if a.full else (a.tl if a.tl is not None else base.get("tl"))
    if tl != base.get("tl") and base["scores"]:
        print(paint(YEL, "Cảnh báo: TL=%s khác TL lúc ghi chuẩn (%s) -> điểm có thể lệch vì thuật toán chạy theo thời gian." % (tl, base.get("tl"))))
    files = sorted((f for f in os.listdir(a.tests) if re.fullmatch(r"Test\d+\.txt", f)), key=lambda f: int(re.findall(r"\d+", f)[0]))
    if a.only:
        want = set(a.only.split(","))
        files = [f for f in files if re.findall(r"\d+", f)[0] in want]
    full_set = not a.only and len(files) == 8
    outdir = os.path.join(HERE, "report_regression"); os.makedirs(outdir, exist_ok=True)
    rows, bad, up, got = [], 0, 0, {}
    print("%-7s %9s %9s %8s %8s  %s" % ("Test", "Chuẩn", "Được", "Giây", "MB", "Kết quả"))
    for f in files:
        name = f[:-4]
        r = harness.run_and_check(a.solution, os.path.join(a.tests, f), os.path.join(outdir, name + ".out"), tl, timeout=900, py=a.python)
        if r["score"] is None:
            verdict = paint(RED, "LỖI: " + r["msg"]); bad += 1
        else:
            got[name] = r["score"]
            b = base["scores"].get(name)
            if b is None:
                verdict = "chưa có điểm chuẩn"
            elif abs(r["score"] - b) < 1e-9:
                verdict = paint(GRN, "KHỚP")
            elif r["score"] < b:
                verdict = paint(RED, "GIẢM %+g" % (r["score"] - b)); bad += 1
            else:
                verdict = paint(YEL, "TĂNG %+g (cập nhật chuẩn bằng --record --force?)" % (r["score"] - b)); up += 1
        print("%-7s %9s %9s %8.1f %8s  %s" % (name, base["scores"].get(name, "-"), "-" if r["score"] is None else "%g" % r["score"], r["time"], "n/a" if r["mem"] is None else "%.0f" % r["mem"], verdict))
    ok_all = len(got) == len(files)
    if full_set and ok_all:
        tot, exp = sum(got.values()), base["total"]
        if abs(tot - exp) < 1e-9:
            msg = paint(GRN, "TỔNG %g == %g  XANH" % (tot, exp))
        elif tot < exp:
            msg = paint(RED, "TỔNG %g < %g  ĐỎ (lệch %+g)" % (tot, exp, tot - exp)); bad += 1
        else:
            msg = paint(YEL, "TỔNG %g > %g  (lệch %+g)" % (tot, exp, tot - exp)); up += 1
        print("\n" + msg)
        if a.record:
            if abs(tot - exp) > 1e-9 and not a.force:
                print(paint(RED, "Không ghi chuẩn: tổng khác %g (dùng --force nếu chắc chắn)." % exp))
            else:
                base["scores"] = got; base["tl"] = tl
                if a.force:
                    base["total"] = tot
                json.dump(base, open(a.baseline, "w", encoding="utf-8"), indent=1)
                print("Đã ghi điểm chuẩn vào", a.baseline)
    elif a.only:
        print("\n(Chạy một phần nên không so tổng.)")
    sys.exit(1 if bad or (up and not a.allow_up) else 0)


if __name__ == "__main__":
    main()
