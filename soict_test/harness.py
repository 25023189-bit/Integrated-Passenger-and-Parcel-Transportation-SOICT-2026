"""Chạy một lần solution như máy chấm (stdin -> stdout), đo thời gian + RAM đỉnh, rồi gọi checker."""
import os, sys, time, subprocess
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import checker

MB = 2.0 ** 20


def _win_peak_mb(handle):
    try:
        import ctypes
        from ctypes import wintypes

        class PMC(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + \
                       [(n, ctypes.c_size_t) for n in ("PeakWorkingSetSize", "WorkingSetSize", "QPPP", "QPP", "QPNP", "QNP", "Pagefile", "PeakPagefile")]
        c = PMC(); c.cb = ctypes.sizeof(c)
        ok = ctypes.windll.psapi.GetProcessMemoryInfo(wintypes.HANDLE(int(handle)), ctypes.byref(c), c.cb)
        return c.PeakWorkingSetSize / MB if ok else None
    except Exception:
        return None


def run_solution(sol, inp, out, tl=None, timeout=600.0, py=None):
    """Trả dict(time, mem, rc, timeout, err). tl=None -> dùng TIME_LIMIT mặc định của solution (250 s)."""
    env = dict(os.environ)
    if tl:
        env["SOICT_TL"] = str(tl)
    errf = out + ".err"
    t0 = time.perf_counter()
    mem = None
    with open(inp, "rb") as fi, open(out, "wb") as fo, open(errf, "wb") as fe:
        p = subprocess.Popen([py or sys.executable, sol], stdin=fi, stdout=fo, stderr=fe, env=env)
        timed_out = False
        if os.name == "nt":
            try:
                p.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True; p.kill(); p.wait()
            rc = p.returncode
            mem = _win_peak_mb(getattr(p, "_handle", 0))
        else:
            import resource  # noqa: F401  (chỉ để chắc chắn nền tảng POSIX)
            while True:
                pid, status, ru = os.wait4(p.pid, os.WNOHANG)
                if pid:
                    break
                if time.perf_counter() - t0 > timeout:
                    timed_out = True; p.kill()
                    pid, status, ru = os.wait4(p.pid, 0); break
                time.sleep(0.01)
            rc = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -os.WTERMSIG(status)
            p.returncode = rc
            mem = ru.ru_maxrss / (MB / 1024.0 if sys.platform == "darwin" else 1024.0)  # Linux: KB, macOS: byte
    el = time.perf_counter() - t0
    err = ""
    try:
        err = open(errf, "rb").read()[-300:].decode("utf8", "replace").strip()
    except Exception:
        pass
    return dict(time=el, mem=mem, rc=rc, timeout=timed_out, err=err)


def run_and_check(sol, inp, out, tl=None, timeout=600.0, py=None):
    r = run_solution(sol, inp, out, tl, timeout, py)
    r["score"], r["msg"] = None, ""
    if r["timeout"]:
        r["msg"] = "quá thời gian chờ"
    elif r["rc"] != 0:
        r["msg"] = "runtime error rc=%s %s" % (r["rc"], r["err"][-120:])
    else:
        try:
            r["score"], r["msg"] = checker.check(inp, out)
        except Exception as ex:
            r["msg"] = "lỗi checker: %r" % (ex,)
    return r
