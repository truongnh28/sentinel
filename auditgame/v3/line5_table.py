"""v3/line5_table.py -- the precomputed line-5 table: belief bins, schema, lookup (T14).

Draft Algorithm 1 line 5, "a_t <- arg min_{pi in Pi} max_{pi_A in Pi_A-hat} L(pi, pi_A | b_t,
B_t)", needs L-hat [28 members x 6 attacker classes] at every task.  Rollouts at every task
do not fit on this machine (v3-p0-chi-phi.md S4), so the PRIMARY source of L-hat (Q13, L1)
is this table, built once on dev by tools/v3_build_table.py with the rollout engine of
v3/rollout.py, and read by line5.TableSource through `Line5Table.lookup`.

THE KEY (plan T14, O16; line5.TableKey)
    table cell   config.table_key_id(cell): (rho, chi, detector) of the PRIMARY world at
                 K_d = 2 and b1 (O14: no budget key; O15: sensitivity worlds and K_d != 2
                 read the primary table, a declared misspecification).  36 table cells.
    Delta-hat    one of config.DELTAS (line 1's output is always on the grid, O3).
    h            tasks left including t, 1..config.TABLE_H_MAX (= H - t).
    belief bin   O16: 5 p_attack levels x 4 top carriers x 2 = 40 bins (`bin_index`):
                    level    number of the cell's four dev-quantile edges (20/40/60/80%) that
                             are <= p_attack (np.searchsorted side="right"): 0..4.  The edges
                             are computed per table cell over every source state of that
                             cell (all Delta-hat, all h) and stored in the table.  Tied edges
                             leave a level empty; its bins fall back (below).
                    carrier  config.CARRIERS.index(BinFeatures.top_carrier).
                    flag     BinFeatures.delegated_high (mass on the delegated carriers > 1/2).
                 bin = (level * 4 + carrier) * 2 + flag.

THE VALUE.  L-hat [28 x 6] (float32) with its Monte Carlo SE (sd / sqrt(n)), the number of
rollouts n behind every entry and the number of source states the rollouts started from.

EMPTY BINS (O16, N3).  A key with no source state takes the values of the NEAREST FILLED
bin with the same (cell, Delta-hat, h), distance |level - level'| + [carrier differs] +
[flag differs], ties to the lower bin index; the reason is stored (REASON_NEAREST_BIN) and
returned in LossMatrix.note.  If no bin of that h is filled, the nearest filled h (ties to
the lower h) with the same bin rule is used (REASON_NEAREST_H) -- a declared extension of
O16, which names only the same h.  A Delta-hat the build did not cover (a pilot) is
REASON_NOT_BUILT and `lookup` raises KeyError: a partial table never answers silently.

SE (O12).  Every filled key has R = 32 rollouts per (member, class); the ABSOLUTE SE (sd of
one member's loss / sqrt(n)) is reported for every entry as a SECONDARY DIAGNOSTIC only
(se, se_flag: se.max() > config.TABLE_SE_MAX = 0.09).  Definition 1's loss is not bounded by
1 (lambda_Q FQ + lambda_T clean lost), so R = 32 alone does not make this bound, and T14's
pilot found it unreachable even at R_MAX = 64 (88% of cells stayed over).

line5-se-diff (27/09/2026, @truong): the top-up GATE is the CRN-paired DIFFERENCE SE
instead -- the quantity line 5's argmin/minimax actually needs is not a member's absolute
loss but WHICH member is better.  v3/rollout.py and tools/v3_build_table.py share one
hypothesis draw, one world seed and one member-randomisation seed across every (member,
class) of a draw r (common random numbers), so the loss samples of two members at the same
r are paired, not independent; sd(loss_i - loss_j) computed from the paired differences is
the right variance to gate on, not sd(loss_i) and sd(loss_j) combined as if independent.
Per key: L-hat's two best members by point estimate of the minimax value V(m) = max_c
L-hat[m, c] (the argmin and its closest competitor) are re-scored on their own per-draw
paired difference (at each member's own argmax class); diff_se = sd(diff) / sqrt(n),
diff_gap = V(second) - V(best).  A key whose diff_se exceeds config.TABLE_DIFF_SE_MAX
(0.15, chosen from a small dev sample across h: see docs/reports/v3-p2-table.md's
27/09/2026 addendum) is topped up once to R_MAX = 64; still over, diff_flag is set and the
note says so.  The old se / se_flag stay in the table and in `lookup`'s note as a secondary
diagnostic; they no longer gate a top-up.

STORAGE.  One .npz, never committed (plan T14, R17); `table_digest()` pins its CONTENT (every
array's name, dtype, shape and bytes, in sorted order), not the file's bytes, because a
zip carries time stamps.  The operating table is TABLE_PATH (P4, after tuning); the P2
pilot is PILOT_PATH.  Both live under spikes/v3-table/, which ignores its own contents.

numpy here (plan S2: numpy for the PF, rollout and table).
"""
from __future__ import annotations

import hashlib
import json
import pathlib

import numpy as np

from v3 import api as A
from v3 import config as C

ROOT = pathlib.Path(__file__).resolve().parent.parent               # auditgame/
TABLE_DIR = ROOT / "spikes" / "v3-table"
#: The operating table (P4, after tuning; pinned by Gate 4 through table_digest()).
TABLE_PATH = TABLE_DIR / "v3_line5_table.npz"
#: The P2 pilot (plan T14: built on dev in the headline table cells, not committed).
PILOT_PATH = TABLE_DIR / "v3_line5_table_pilot.npz"

SCHEMA_VERSION = 1
DELTA_KEYS = tuple(C.DELTAS)                  # (0, 1, 2, 4, 8)
H_MAX = C.TABLE_H_MAX                         # 14
N_BINS = C.N_BELIEF_BINS                      # 40
P_LEVELS = C.BIN_P_ATTACK_LEVELS              # 5
N_CARRIERS = C.BIN_TOP_CARRIER_LEVELS         # 4
#: O16: the quantiles of p_attack whose values are the level edges.
QUANTILES = tuple((i + 1) / P_LEVELS for i in range(P_LEVELS - 1))   # 0.2, 0.4, 0.6, 0.8
#: O12.
R = C.TABLE_R                                 # 32
R_MAX = 2 * C.TABLE_R                         # 64: one top-up (plan S8 "R = 32-64")
SE_MAX = C.TABLE_SE_MAX                       # 0.09: secondary diagnostic, no longer the gate
DIFF_SE_MAX = C.TABLE_DIFF_SE_MAX             # 0.15: line5-se-diff top-up gate (27/09/2026)

REASON_FILLED = 0
REASON_NEAREST_BIN = 1
REASON_NEAREST_H = 2
REASON_NOT_BUILT = 3
REASON_EMPTY = 4                              # built, but no source state in the whole row
REASONS = {REASON_FILLED: "filled", REASON_NEAREST_BIN: "nearest bin, same h (O16)",
           REASON_NEAREST_H: "no filled bin at this h: nearest h, then nearest bin",
           REASON_NOT_BUILT: "Delta-hat not built in this table",
           REASON_EMPTY: "no source state at any h for this Delta-hat"}

ARRAYS = ("L", "se", "n", "states", "src", "reason", "se_flag",
          "diff_se", "diff_gap", "diff_flag", "diff_pair")


# ---------------------------------------------------------------------------------------
# Bins (O16)
# ---------------------------------------------------------------------------------------


def edges_of(p_values) -> tuple:
    """The four p_attack level edges: dev quantiles 20/40/60/80% (numpy's linear rule)."""
    p = np.asarray(list(p_values), float)
    if p.size == 0:
        raise ValueError("no source state: the p_attack edges are undefined")
    return tuple(float(x) for x in np.quantile(p, QUANTILES))


def p_level(p_attack: float, edges) -> int:
    return int(np.searchsorted(np.asarray(edges, float), float(p_attack), side="right"))


def bin_of(level: int, carrier: int, flag: int) -> int:
    return (level * N_CARRIERS + carrier) * 2 + flag


def bin_coords(b: int) -> tuple:
    """bin -> (level, carrier index, flag)."""
    return b // (2 * N_CARRIERS), (b // 2) % N_CARRIERS, b % 2


def bin_key(features: A.BinFeatures, edges) -> int:
    """O16: 5 p_attack levels x top carrier x delegated flag -> 0..39."""
    if features.top_carrier not in C.CARRIERS:
        raise ValueError(f"top_carrier {features.top_carrier!r} is not one of {C.CARRIERS}")
    return bin_of(p_level(features.p_attack, edges), C.CARRIERS.index(features.top_carrier),
                  int(bool(features.delegated_high)))


def bin_distance(a: int, b: int) -> int:
    la, ca, fa = bin_coords(a)
    lb, cb, fb = bin_coords(b)
    return abs(la - lb) + int(ca != cb) + int(fa != fb)


def nearest_bin(b: int, filled) -> int | None:
    """The filled bin nearest to b (bin_distance; ties to the lower index), or None."""
    cands = sorted(filled)
    if not cands:
        return None
    return min(cands, key=lambda x: (bin_distance(b, x), x))


def h_pos(h: int) -> int:
    if isinstance(h, bool) or not isinstance(h, (int, np.integer)) or not 1 <= h <= H_MAX:
        raise KeyError(f"h={h!r} is not a remaining length in 1..{H_MAX}")
    return int(h) - 1


def delta_pos(delta_hat) -> int:
    if isinstance(delta_hat, bool) or delta_hat not in DELTA_KEYS:
        raise KeyError(f"Delta-hat={delta_hat!r} is not one of the table's {DELTA_KEYS} (O3: "
                       f"line 1 rounds down onto the grid)")
    return DELTA_KEYS.index(delta_hat)


def flat(d: int, hi: int, b: int) -> int:
    return (d * H_MAX + hi) * N_BINS + b


def unflat(i: int) -> tuple:
    return i // (H_MAX * N_BINS), (i // N_BINS) % H_MAX, i % N_BINS


# ---------------------------------------------------------------------------------------
# Filling empty keys (O16)
# ---------------------------------------------------------------------------------------


def resolve_fallbacks(filled: np.ndarray, built_deltas) -> tuple:
    """filled: bool [5, 14, 40].  Returns (src int32 [5, 14, 40], reason int8 [5, 14, 40]):
    the flat index of the key whose values each key uses, and why."""
    src = np.full(filled.shape, -1, np.int32)
    reason = np.full(filled.shape, REASON_NOT_BUILT, np.int8)
    for d in range(len(DELTA_KEYS)):
        if DELTA_KEYS[d] not in built_deltas:
            continue
        rows = {hi: [b for b in range(N_BINS) if filled[d, hi, b]] for hi in range(H_MAX)}
        have = [hi for hi in range(H_MAX) if rows[hi]]
        for hi in range(H_MAX):
            for b in range(N_BINS):
                if filled[d, hi, b]:
                    src[d, hi, b], reason[d, hi, b] = flat(d, hi, b), REASON_FILLED
                elif rows[hi]:
                    src[d, hi, b] = flat(d, hi, nearest_bin(b, rows[hi]))
                    reason[d, hi, b] = REASON_NEAREST_BIN
                elif have:
                    h2 = min(have, key=lambda x: (abs(x - hi), x))
                    src[d, hi, b] = flat(d, h2, nearest_bin(b, rows[h2]))
                    reason[d, hi, b] = REASON_NEAREST_H
                else:
                    reason[d, hi, b] = REASON_EMPTY
    return src, reason


# ---------------------------------------------------------------------------------------
# Content digest
# ---------------------------------------------------------------------------------------


def content_digest(arrays: dict) -> str:
    """sha256 over every array's name, dtype, shape and bytes, sorted by name."""
    h = hashlib.sha256()
    for name in sorted(arrays):
        a = np.ascontiguousarray(arrays[name])
        h.update(name.encode("utf-8") + b"\0" + str(a.dtype).encode("ascii") + b"\0"
                 + json.dumps(list(a.shape)).encode("ascii") + b"\0")
        h.update(a.tobytes())
    return "sha256:" + h.hexdigest()


def file_digest(path) -> str:
    with np.load(path, allow_pickle=False) as z:
        return content_digest({k: z[k] for k in z.files})


def table_digest(path=None) -> str | None:
    """The operating line-5 table's content digest (seal.LIVE_DIGESTS, freeze_v3), or None
    when it is not built (P2: only the pilot exists, so eval stays sealed)."""
    p = pathlib.Path(path) if path is not None else TABLE_PATH
    return file_digest(p) if p.exists() else None


# ---------------------------------------------------------------------------------------
# The table
# ---------------------------------------------------------------------------------------


def _meta_array(meta: dict) -> np.ndarray:
    return np.frombuffer(C.canonical_json(meta).encode("ascii"), np.uint8).copy()


class Line5Table:
    """The table in memory.  meta: members, classes, cells {table_cell_id: {rho, chi,
    dprime, edges, built_deltas}}, build settings.  cells[id] = {array name: ndarray}."""

    def __init__(self, meta: dict, cells: dict):
        self.meta = meta
        self.cells = cells
        self.members = tuple(meta["members"])
        self.classes = tuple(meta["classes"])
        self._cache: dict = {}
        for cid, arr in cells.items():
            if cid not in meta["cells"]:
                raise ValueError(f"table cell {cid} has arrays but no meta")
            missing = [a for a in ARRAYS if a not in arr]
            if missing:
                raise ValueError(f"table cell {cid} lacks {missing}")
            shape = (len(DELTA_KEYS), H_MAX, N_BINS)
            if arr["L"].shape != shape + (len(self.members), len(self.classes)):
                raise ValueError(f"table cell {cid}: L has shape {arr['L'].shape}")

    # ---- io --------------------------------------------------------------------------
    def arrays(self) -> dict:
        out = {"meta": _meta_array(self.meta)}
        for cid in sorted(self.cells):
            for a in ARRAYS:
                out[f"{cid}/{a}"] = self.cells[cid][a]
        return out

    def digest(self) -> str:
        return content_digest(self.arrays())

    def save(self, path) -> str:
        path = pathlib.Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(path, **self.arrays())
        return self.digest()

    @classmethod
    def load(cls, path) -> "Line5Table":
        with np.load(path, allow_pickle=False) as z:
            meta = json.loads(z["meta"].tobytes().decode("ascii"))
            cells = {cid: {a: z[f"{cid}/{a}"] for a in ARRAYS} for cid in meta["cells"]}
        return cls(meta, cells)

    # ---- lookup (line5.TableSource) --------------------------------------------------
    def entry(self, table_cell: str, delta_hat, h: int, b: int) -> tuple:
        """(source flat index, reason code) of one key; KeyError if not answerable."""
        if table_cell not in self.cells:
            raise KeyError(f"table cell {table_cell} is not in this table (built: "
                           f"{sorted(self.cells)})")
        d, hi = delta_pos(delta_hat), h_pos(h)
        if not 0 <= b < N_BINS:
            raise KeyError(f"bin {b} is not in 0..{N_BINS - 1}")
        arr = self.cells[table_cell]
        r = int(arr["reason"][d, hi, b])
        if r in (REASON_NOT_BUILT, REASON_EMPTY):
            raise KeyError(f"table cell {table_cell}, Delta-hat {delta_hat}, h {h}, bin {b}: "
                           f"{REASONS[r]}")
        return int(arr["src"][d, hi, b]), r

    def lookup(self, key) -> A.LossMatrix:
        """line5.TableKey -> api.LossMatrix (source 'table'); `note` says where the values
        come from when the key's own bin is empty (O16) and flags SE over 0.09 (O12)."""
        meta = self.meta["cells"].get(key.table_cell)
        if meta is None:
            raise KeyError(f"table cell {key.table_cell} is not in this table")
        b = bin_key(key.features, meta["edges"])
        ck = (key.table_cell, key.delta_hat, key.h, b)
        hit = self._cache.get(ck)
        if hit is not None:
            return hit
        s, r = self.entry(key.table_cell, key.delta_hat, key.h, b)
        arr = self.cells[key.table_cell]
        sd, shi, sb = unflat(s)
        Lm = arr["L"][sd, shi, sb].astype(float)
        se = arr["se"][sd, shi, sb].astype(float)
        n = int(arr["n"][sd, shi, sb])
        notes = [f"bin {b} (level {bin_coords(b)[0]}, {C.CARRIERS[bin_coords(b)[1]]}, "
                 f"flag {bin_coords(b)[2]}); states {int(arr['states'][sd, shi, sb])}; R {n}"]
        if r != REASON_FILLED:
            notes.append(f"{REASONS[r]}: values of Delta-hat {DELTA_KEYS[sd]}, h {shi + 1}, "
                         f"bin {sb}")
        diff_se = float(arr["diff_se"][sd, shi, sb])
        notes.append(f"diff-SE {diff_se:.4f} (pair {tuple(int(x) for x in arr['diff_pair'][sd, shi, sb])}, "
                     f"gap {float(arr['diff_gap'][sd, shi, sb]):.4f})")
        if bool(arr["diff_flag"][sd, shi, sb]):
            notes.append(f"diff-SE {diff_se:.4f} > {DIFF_SE_MAX} after R = {n} "
                         f"(O12, line5-se-diff)")
        if bool(arr["se_flag"][sd, shi, sb]):
            notes.append(f"secondary diagnostic: SE {float(se.max()):.4f} > {SE_MAX} "
                         f"after R = {n} (not gated)")
        m = A.LossMatrix(self.members, self.classes,
                         tuple(tuple(float(x) for x in row) for row in Lm),
                         tuple(tuple(float(x) for x in row) for row in se),
                         tuple(tuple(n for _ in self.classes) for _ in self.members),
                         "table", "; ".join(notes))
        self._cache[ck] = m
        return m

    # ---- summaries (report) ----------------------------------------------------------
    def summary(self) -> dict:
        out = {}
        for cid, arr in self.cells.items():
            built = [DELTA_KEYS.index(d) for d in self.meta["cells"][cid]["built_deltas"]]
            rs = arr["reason"][built]
            filled = rs == REASON_FILLED
            se = arr["se"][built].max(axis=(-1, -2))[filled]
            diff_se = arr["diff_se"][built][filled]
            out[cid] = {"keys": int(rs.size), "filled": int(filled.sum()),
                        "nearest_bin": int((rs == REASON_NEAREST_BIN).sum()),
                        "nearest_h": int((rs == REASON_NEAREST_H).sum()),
                        "empty_row": int((rs == REASON_EMPTY).sum()),
                        "topped_up": int((arr["n"][built][filled] > R).sum()),
                        # line5-se-diff (27/09/2026): the gate.
                        "diff_se_max": float(diff_se.max()) if diff_se.size else None,
                        "diff_se_median": float(np.median(diff_se)) if diff_se.size else None,
                        "diff_flagged": int(arr["diff_flag"][built][filled].sum()),
                        # secondary diagnostic (no longer gated).
                        "se_max": float(se.max()) if se.size else None,
                        "se_median": float(np.median(se)) if se.size else None,
                        "se_flagged": int(arr["se_flag"][built][filled].sum())}
        return out


def empty_cell(n_members: int, n_classes: int) -> dict:
    shape = (len(DELTA_KEYS), H_MAX, N_BINS)
    return {"L": np.zeros(shape + (n_members, n_classes), np.float32),
            "se": np.zeros(shape + (n_members, n_classes), np.float32),
            "n": np.zeros(shape, np.int16), "states": np.zeros(shape, np.int16),
            "src": np.full(shape, -1, np.int32),
            "reason": np.full(shape, REASON_NOT_BUILT, np.int8),
            "se_flag": np.zeros(shape, bool),
            "diff_se": np.zeros(shape, np.float32), "diff_gap": np.zeros(shape, np.float32),
            "diff_flag": np.zeros(shape, bool),
            "diff_pair": np.full(shape + (2,), -1, np.int16)}


def load(path=None) -> Line5Table:
    return Line5Table.load(TABLE_PATH if path is None else path)


def load_table(path=None) -> Line5Table:
    """The table T15's Sentinel reads: an object with lookup(line5.TableKey) ->
    api.LossMatrix (source 'table').  Default: the operating table TABLE_PATH; pass
    PILOT_PATH for the P2 pilot."""
    return load(path)
