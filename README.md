# Integrated Passenger and Parcel Transportation — SOICT 2026

[![arXiv](https://img.shields.io/badge/arXiv-2611.22043-b31b1b.svg)](https://arxiv.org/abs/2611.22043)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

A hybrid **exact–heuristic solver** for the *Integrated Passenger and Parcel Transportation* problem of the
SOICT 2026 Student Contest (round 2): a selective pickup-and-delivery routing problem with time windows,
open routes and heterogeneous taxis. The solver is a single Python 3.8 file that uses only the standard library.

**Technical report:** [A Hybrid Exact-Heuristic Solver for the Integrated Passenger and Parcel Transportation Problem — arXiv:2611.22043](https://arxiv.org/abs/2611.22043)

<details>
<summary><b>Tiếng Việt (tóm tắt)</b></summary>

Mã nguồn giải bài toán *Vận tải tích hợp hành khách và bưu kiện* của cuộc thi SOICT 2026 (vòng 2): chọn các yêu cầu
khách/bưu kiện để phục vụ, gán cho taxi và sắp thứ tự điểm dừng sao cho lợi nhuận (doanh thu trừ chi phí di chuyển)
lớn nhất, trong giới hạn 5 phút mỗi test. Chương trình là một file Python 3.8, chỉ dùng thư viện chuẩn. Với test cỡ nhỏ
và vừa, chương trình liệt kê route cho từng taxi rồi giải bài toán chọn route bằng nhánh cận (kết hợp LNS trên route,
cận Lagrange và loại route theo reduced cost). Với test cỡ lớn, nơi số route quá nhiều, chương trình dùng ALNS.
Mọi lời giải đều được kiểm tra bằng bộ verify độc lập trước khi in. Kết quả chính thức: tổng lợi nhuận **487.237**
trên 38 test được tính điểm. Chi tiết xem báo cáo trên arXiv ở trên.

</details>

## Problem

A company has *K* taxis. Each taxi starts at its own depot at time 0, may finish anywhere, and has a parcel capacity.
There are *N* passenger requests and *M* parcel requests; every request has a revenue and may be rejected, but a served
request is served completely by exactly one taxi.

* A passenger is driven **directly** from pickup to drop-off; no other request point may be visited in between.
* A parcel is picked up and delivered by the same taxi (pickup first) and counts towards the taxi's load while on board.
* Pickups (and parcel deliveries) have time windows; arriving early means waiting, arriving late is infeasible.
* Travel times and costs are directed and need not satisfy the triangle inequality.

The goal is to maximize **benefit = total revenue of served requests − total travel cost**.
The official problem statement belongs to the contest organizers and is not redistributed here; see the SOICT 2026
contest materials.

## Results

Official round-2 evaluation (Python 3.8, 5-minute limit, 39 test cases of which 38 count towards the score):

| Run time | # instances | Total benefit | Share | Max time (s) | Max memory (MB) |
|---|---:|---:|---:|---:|---:|
| ≤ 5 s | 22 | 61,588 | 12.6 % | 4.0 | 184.5 |
| 5 – 61 s | 6 | 96,773 | 19.9 % | 60.9 | 250.8 |
| ≥ 269 s (time limit) | 10 | 328,876 | 67.5 % | 276.9 | 278.6 |
| **Total** | **38** | **487,237** | 100 % | 276.9 | 278.6 |

The ten instances that use the whole budget are the large ones and carry two thirds of the total benefit.
Because the search loops are time-limited, results depend slightly on the speed of the machine.

## How it works

```
Greedy insertion ──► Local search ──► Route enumeration (3 attempts: unrestricted, ≤4, ≤3 requests/route)
                                           │ success                          │ all attempts fail
                                           ▼                                  ▼
                              Exact route selection                      ALNS + polish
                      (branch-and-bound + route-LNS +
                       Lagrangian bound + reduced-cost fixing)
                                           └──────────────► Independent verifier ──► output
```

* **Fast feasibility.** Routes store the *latest feasible arrival* of every stop, so an insertion position is tested in
  O(1). Every accepted change is re-evaluated from scratch, so the stored solution is always feasible.
* **Heuristic engine.** Greedy insertion, local search (relocate / swap / replace) and an Adaptive Large Neighborhood
  Search with random, worst and Shaw removal, greedy and regret-2/3 repair, simulated-annealing acceptance with a
  time-based cooling schedule, and adaptive operator weights.
* **Exact engine.** For each taxi a depth-first search enumerates feasible routes and keeps, for every set of
  requests, only the cheapest route. The remaining set-packing problem is solved by branch-and-bound with symmetry
  breaking between identical taxis, route-based LNS, a Lagrangian upper bound and reduced-cost fixing.
* **Preprocessing.** Hopeless requests are removed (earliest-arrival Dijkstra from all depots); parcel pickup
  deadlines are tightened when the triangle inequality holds on a random sample; candidate lists are filtered by
  reachability and sorted by deadline (binary search); identical taxis share one route pool; request sets are
  compressed into short bit masks.
* **Safety.** Only verified solutions are printed (fallback: the greedy solution), every loop checks the deadline,
  and a `SIGALRM` watchdog at 290 s prints the best verified solution if anything overruns.

See the [technical report](https://arxiv.org/abs/2611.22043) for pseudocode and details.

## Repository layout

```
.
├── src/        # the solver (the exact file submitted in round 2)
├── docs/       # technical report, slides and notes
├── data/       # practice instances (see the note on data below)
├── README.md
├── LICENSE
└── CITATION.cff
```

<!-- TODO: adjust the folder and file names above to match the repository after renaming. -->

## Usage

Requirements: **Python 3.8 or newer**, no external packages. The watchdog uses `SIGALRM`, so it is active on
Linux/macOS; on Windows it is skipped and only the deadline checks inside the loops apply.

```bash
# read from a file, write to a file
python src/solution.py data/2_2_2.txt out.txt

# or use standard input / output
python src/solution.py < data/2_2_2.txt > out.txt

# shorter time limit for quick experiments (seconds; default 270)
SOICT_TL=30 python src/solution.py data/10_50_50.txt out.txt
```

On the smallest practice instance (2 taxis, 2 passengers, 2 parcels) the first output line is `217`.

Optional switches (set to `0` to disable): `SOICT_SORT` (candidate sorting), `SOICT_SYM` (identical-taxi grouping),
`SOICT_COMPRESS` (request elimination and mask compression). They exist for experiments and ablations.

### Input format

```
K N M
<depot node> <capacity Q>                                  (K lines)
P D E L S T                                                (N passenger lines)
P D w Ep Lp Ed Ld S T                                      (M parcel lines)
V x V travel-time matrix                                   (V = K + 2N + 2M)
V x V travel-cost matrix
```

Nodes are numbered from 1: depots first, then the pickup and drop-off of each request.
A passenger line is `pickup drop-off earliest latest service revenue`; a parcel line is
`pickup delivery weight pickup-earliest pickup-latest delivery-earliest delivery-latest service revenue`.

### Output format

```
<benefit>
<n_1> <node> <node> ...        (one line per taxi: number of stops, then the stops in order; depot not printed)
...
<n_K> ...
```

A taxi that stays idle is printed as `0`. The benefit on the first line is recomputed by the independent verifier.

## Authors and contributions

| Author | Contribution |
|---|---|
| **Bùi Thế Dũng** (first author) | Main idea and design of the whole approach, and the technical report. |
| **Nguyễn Hà Thu** (second author) | Implementation of the solver. Also found a refinement of the preprocessing step during implementation. |

<!-- TODO: confirm which preprocessing refinement is credited to N. H. Thu and edit the sentence above. -->

Both authors are students at the University of Engineering and Technology, Vietnam National University, Hanoi (UET-VNU).
On arXiv the names appear as *The Dung Bui* and *Ha Thu Nguyen*.

## AI assistance

Generative AI tools were used during development (code review, experiments and drafting of documentation and report
text). The authors reviewed the material and take full responsibility for the code and the paper.

<!-- TODO: edit this paragraph so that it describes exactly how AI tools were used. -->

## Notes on data

The practice instances in `data/` come from the SOICT 2026 contest. They are provided for reproducibility only and are
**not** covered by the license of this repository; their rights remain with the contest organizers. Remove them from the
public repository if the contest rules do not allow redistribution.

## Citation

If you use this code or build on the report, please cite:

```bibtex
@misc{bui2026hybrid,
  title         = {A Hybrid Exact-Heuristic Solver for the Integrated Passenger and Parcel Transportation Problem},
  author        = {Bui, The Dung and Nguyen, Ha Thu},
  year          = {2026},
  eprint        = {2611.22043},
  archivePrefix = {arXiv},
  primaryClass  = {cs.AI},
  url           = {https://arxiv.org/abs/2611.22043}
}
```

GitHub also shows a *Cite this repository* button based on [`CITATION.cff`](CITATION.cff).

## License

The source code is released under the [MIT License](LICENSE).
The technical report is distributed through arXiv under arXiv's own license; the problem statement and the contest
instances belong to the SOICT 2026 organizers and are not covered by this license.

## Acknowledgements

Thanks to the SOICT 2026 organizers for the contest and the problem statement (Dr. Pham Quang Dung and
Dr. Quang Huy Duong, Hanoi University of Science and Technology; Dr. Hung Son Nguyen, University of Warsaw).
