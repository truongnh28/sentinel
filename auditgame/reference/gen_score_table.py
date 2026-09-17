#!/usr/bin/env python3
"""
gen_score_table.py -- Generates the CARRIER SCORE REFERENCE TABLE for AuditGame-SE.

This is B0.5's first artifact (see eval/SPEC-Tang-Do-va-Test.md SS2.5-2.6).
ONE table serves THREE consumers, which is why it must freeze as a single block:

  1. tau_sel(n_c, d', K)   -> B5/B6's carrier-selection threshold; FP = 5% PER TASK
  2. E[p_c | clean, n]     -> drift diagnostics (test_drift_matches_reference_table)
  3. E[X^3/(1+pi0 X)]      -> the left side of the sandwich bound
                              (test_weighted_lambda_scale_is_right_skewed)

Re-running with the same seed must produce EXACTLY this file (I1).  Every parameter
that produced it lives in the JSON's own `provenance` block -- no hidden parameters
(I5).

    python3 gen_score_table.py            # write score_table.json
    python3 gen_score_table.py --check    # regenerate, compare to the existing file, write nothing

TWO KINDS OF ROW, TWO KINDS OF INPUT.

  * weak / mid / strong -- keyed by the manuscript's declared (psi, phi) pair.
    Both the detection rate and the false-alarm rate differ between them.

  * d0.0 .. d3.0 -- keyed by d' ITSELF, one row per point of dprime_sweep.GRID
    (0.0 .. 3.0, step 0.2).  Name format: "d" followed by d' at ONE decimal,
    `f"d{d_prime:.1f}"` -- see sweep_setting_name(), and the gate-2 test
    test_the_following_mode_reads_the_tau_sel_row_calibrated_at_the_swept_d_prime
    pins the sweep's spelling of the same name against it.

    For these rows the false-alarm rate is FIXED at phi = SWEEP_PHI = 0.12, so
    tau_detector = z(1 - phi) is one constant and ONLY d' varies down the list.
    That is not a convenience: it is the same contract dprime_sweep.py states for
    the curve itself ("every point on the curve is the SAME false-alarm rate").
    A tau_sel row whose phi drifted with d' would re-introduce the second
    dimension the sweep exists to remove, and the threshold would then be
    calibrated against something other than the detector actually running.

    psi is REPORTED for these rows (psi = Phi(d' - tau_det)) but is derived, not
    an input -- the row is a function of d' alone.

WHY THE ADDITION IS SAFE.  Each setting draws from `random.Random(SEED ^
hash_name(name))`, a stream keyed by its own NAME, and the rows of one setting
never touch another setting's stream.  Adding names therefore leaves weak / mid /
strong BYTE-IDENTICAL.  That is checked, not asserted:
tests/gate1_integrity/test_score_table_generator.py runs this build() with N_MAX
cut to 1 and compares each frozen setting's n=0/n=1 rows -- the first cells its
stream ever feeds -- against the committed file.

FROZEN STRINGS.  The Vietnamese text inside `provenance` (and the empty-carrier
`note`) is CONTENT OF THE FROZEN ARTIFACT, not source prose.  Translating it
changes score_table.json and makes --check report a mismatch, so it stays
byte-identical.  Regenerating is not a cheap way out either: M=800k samples across
31 values of n and 19 settings is on the order of 7 billion Gaussian draws, about
23 minutes.
"""
from __future__ import annotations
import argparse, json, math, random, statistics, sys, hashlib, datetime, pathlib

PI0 = 0.10                    # per-item prior -- a MODEL CONSTANT, see SPEC SS2.6
N_MAX = 30                    # real n_c <= 20; build out to 30 for headroom
M = 800_000                   # samples per cell
SEED = 20260915
ALPHA_TASK = 0.05             # false-positive budget PER TASK (not per carrier)
K_MAX = 4                     # max carriers scored within one task

# The manuscript's SS8 (psi, phi) -> (d', tau_detector) per SPEC SS2.1
SETTINGS = {"weak": (0.75, 0.20), "mid": (0.85, 0.12), "strong": (0.92, 0.06)}

# The d'-keyed rows: dprime_sweep.py's grid, at the sweep's own fixed phi.
SWEEP_PHI = 0.12                                          # = mid's phi, the sweep's tau_det
SWEEP_GRID = tuple(round(0.2 * i, 2) for i in range(16))  # 0.0 .. 3.0, step 0.2

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "score_table.json"


def _z(q: float) -> float:
    return statistics.NormalDist().inv_cdf(q)


def d_prime_and_tau(psi: float, phi: float) -> tuple[float, float]:
    """d' = z(psi) - z(phi),  tau_det = z(1-phi).  SPEC SS2.1.

    tau_det is the ITEM-level threshold on the RAW score -- a DIFFERENT object from
    tau_sel (carrier level, on the posterior).
    """
    return _z(psi) - _z(phi), _z(1.0 - phi)


def sweep_setting_name(d_prime: float) -> str:
    """Stable name of a d'-keyed row: "d" + d' at one decimal -- d0.0 .. d3.0.

    ONE decimal is enough for dprime_sweep.GRID (step 0.2) and no more than that:
    a wider format would invite lookups at the sweep's step-0.05 refinement points,
    for which no row is generated and none could be, since the refinement bracket
    is only known after the coarse grid has been measured.
    """
    return f"d{d_prime:.1f}"


def post(lam: float) -> float:
    """Posterior from a likelihood ratio. p = pi0*L / (pi0*L + 1 - pi0)."""
    return PI0 * lam / (PI0 * lam + 1.0 - PI0)


def measure(d_prime: float, n: int, rng: random.Random) -> dict:
    """One cell of the table: a carrier of n CLEAN items, aggregated by mean-Lambda."""
    if n == 0:
        # An empty carrier = NOT YET OBSERVED, not known clean.  Lambda_bar = 1 => p = pi0.
        return dict(n=0, mean_p=PI0, se_mean_p=0.0,
                    tau_sel={str(k): PI0 for k in range(1, K_MAX + 1)},
                    mean_cubic=0.0, se_cubic=0.0, note="rỗng: không bằng chứng, p = pi0")

    half = d_prime * d_prime / 2.0
    ps, cubics = [], []
    for _ in range(M):
        lam_bar = sum(math.exp(d_prime * rng.gauss(0.0, 1.0) - half)
                      for _ in range(n)) / n
        x = lam_bar - 1.0
        ps.append(post(lam_bar))
        cubics.append(x ** 3 / (1.0 + PI0 * x))

    ps.sort()
    # tau_sel[K] = the (1 - alpha_c(K)) quantile, with alpha_c(K) = 1 - (1-alpha_task)^(1/K).
    # Keeps FP = alpha_task PER TASK however many carriers are scored.
    tau_sel = {}
    for k in range(1, K_MAX + 1):
        alpha_c = 1.0 - (1.0 - ALPHA_TASK) ** (1.0 / k)
        tau_sel[str(k)] = ps[min(int((1.0 - alpha_c) * M), M - 1)]
    return dict(
        n=n,
        mean_p=statistics.fmean(ps),
        se_mean_p=statistics.stdev(ps) / math.sqrt(M),
        tau_sel=tau_sel,
        mean_cubic=statistics.fmean(cubics),
        se_cubic=statistics.stdev(cubics) / math.sqrt(M),
    )


def one_table(name: str, dp: float, tau_det: float, psi: float, phi: float) -> dict:
    """One setting's 31 rows, drawn from the stream keyed by that setting's NAME.

    The name is the ONLY thing that picks the stream, which is what makes adding
    settings an additive change: nothing here reads the registry it came from.
    """
    V = math.exp(dp * dp) - 1.0
    C = PI0 * PI0 * (1.0 - PI0) * V              # sandwich-bound coefficient, SPEC SS2.5
    rng = random.Random(SEED ^ hash_name(name))
    rows = [measure(dp, n, rng) for n in range(N_MAX + 1)]
    return dict(
        psi=psi, phi=phi, d_prime=dp, tau_detector=tau_det,
        var_lambda=V, bound_coefficient_C=C,
        n_min_bound_useful=C / PI0,               # below this, -pi0 is the binding side
        rows=rows,
    )


def build(progress=None) -> dict:
    tables = {}
    for name, (psi, phi) in SETTINGS.items():
        dp, tau_det = d_prime_and_tau(psi, phi)
        if progress:
            progress(name, dp)
        tables[name] = one_table(name, dp, tau_det, psi, phi)

    # d'-keyed rows: phi FIXED, psi DERIVED, only d' varies.  See module docstring.
    tau_det = _z(1.0 - SWEEP_PHI)
    for dp in SWEEP_GRID:
        name = sweep_setting_name(dp)
        if progress:
            progress(name, dp)
        tables[name] = one_table(name, dp, tau_det,
                                 statistics.NormalDist().cdf(dp - tau_det), SWEEP_PHI)
    return tables


def hash_name(s: str) -> int:
    return int.from_bytes(hashlib.blake2b(s.encode(), digest_size=4).digest(), "big")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="regenerate and compare to the existing file; write nothing")
    a = ap.parse_args()

    # Progress on stderr: a full run is ~23 minutes (19 tables x 31 cells x 800k
    # samples) and a silent 23-minute process is indistinguishable from a hung one.
    def progress(name, dp):
        print(f"  building [{name}] d'={dp:.3f} ...", file=sys.stderr, flush=True)

    tables = build(progress)
    doc = {
        "provenance": {
            "generated_by": "auditgame/reference/gen_score_table.py",
            "spec": "eval/SPEC-Tang-Do-va-Test.md §2.5-2.6",
            "measured_at": datetime.date.today().isoformat(),
            "status": "MEASURED",
            "seed": SEED,
            "samples_per_cell": M,
            "pi0": PI0,
            "n_max": N_MAX,
            "settings_declared": "weak/mid/strong -- khoá bằng cặp (psi, phi) của bản thảo §8",
            "settings_by_dprime": ("d0.0 .. d3.0 -- khoá bằng CHÍNH d', một hàng cho mỗi điểm của "
                                   "lưới quét dprime_sweep.GRID (0.0..3.0, bước 0.2). Tên hàng: "
                                   "f\"d{d_prime:.1f}\"."),
            "sweep_phi": SWEEP_PHI,
            "settings_by_dprime_note": ("Các hàng d' GIỮ CỐ ĐỊNH phi = 0.12 (tau_det = z(1-phi)), "
                                        "psi = Phi(d'-tau_det) là ĐẠI LƯỢNG DẪN XUẤT chứ không phải "
                                        "đầu vào -- cùng một giao kèo 'mọi điểm cùng một tỉ lệ báo "
                                        "động giả' mà dprime_sweep.py phát biểu cho đường cong. "
                                        "Nếu phi trôi theo d' thì tau_sel lại phụ thuộc hai chiều "
                                        "và confound không gỡ được."),
            "additive": ("RNG mỗi setting là random.Random(SEED ^ hash_name(TÊN)) nên THÊM setting "
                         "không làm xê dịch weak/mid/strong: ba bảng cũ BYTE-IDENTICAL."),
            "aggregation": "mean-Lambda: p_c = pi0*mean(Lambda_i) / (pi0*mean(Lambda_i) + 1 - pi0)",
            "alpha_task": ALPHA_TASK,
            "threshold_rule": ("tau_sel(n_c, d', K) = phân vị (1 - alpha_c(K)) của p_c trên carrier sạch, "
                               "alpha_c(K) = 1-(1-alpha_task)^(1/K). Giữ FP = alpha_task MỖI TASK, "
                               "bất kể K carrier được chấm. K_t tăng theo t nên alpha_c cố định sẽ trôi dọc trục RQ1."),
            "tau_det_note": "tau_det (ngưỡng mức item, trên điểm THÔ) là vật thể KHÁC: z(1-phi), do manuscript §8 quy định.",
            "empty_carrier": "p_c = pi0 (chưa quan sát, KHÔNG phải đã biết sạch)",
            "identity": "E[p_c|sạch,n] - pi0 = -pi0^2 (1-pi0) E[X^2/(1+pi0 X)],  X = Lambda_bar - 1",
            "bound": "max(-C/n, -pi0) < E[p_c|sạch,n] - pi0 < 0,  C = pi0^2 (1-pi0)(e^{d'^2}-1)",
            "bound_left_status": "THỰC NGHIỆM — tương đương chính xác với E[X^3/(1+pi0 X)] >= 0; chưa có chứng minh",
            "python": sys.version.split()[0],
            "warning": "KHÔNG sửa tay. Sửa script rồi sinh lại, nếu không I1 và I5 cùng đỏ.",
        },
        "tables": tables,
    }
    blob = json.dumps(doc, indent=2, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(blob.encode()).hexdigest()

    if a.check:
        if not OUT.exists():
            print("CHECK: file does not exist"); return 1
        cur = json.loads(OUT.read_text(encoding="utf-8"))
        cur.get("provenance", {}).pop("measured_at", None)
        new = json.loads(blob); new["provenance"].pop("measured_at", None)
        same = cur == new
        print(f"CHECK: {'MATCH' if same else 'MISMATCH'}")
        return 0 if same else 1

    OUT.write_text(blob, encoding="utf-8")
    print(f"wrote {OUT}")
    print(f"sha256 {digest}")
    for name, t in tables.items():
        r = {x["n"]: x for x in t["rows"]}
        print(f"\n[{name}] d'={t['d_prime']:.3f}  C={t['bound_coefficient_C']:.4f}  "
              f"the -C/n bound is useful when n > {t['n_min_bound_useful']:.1f}")
        print(f"  {'n':>3}{'E[p|clean]':>12}{'deficit':>12}"
              + "".join(f"{'tau_sel K='+str(k):>13}" for k in range(1, K_MAX + 1)))
        for n in (0, 1, 2, 5, 9, 20, 30):
            x = r[n]
            print(f"  {n:>3}{x['mean_p']:>12.5f}{x['mean_p']-PI0:>12.5f}"
                  + "".join(f"{x['tau_sel'][str(k)]:>13.4f}" for k in range(1, K_MAX + 1)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
