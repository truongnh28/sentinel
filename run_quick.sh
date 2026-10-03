#!/usr/bin/env bash
# Chạy nhanh Sentinel v3: cài môi trường, kiểm tra bản đóng băng, chạy bộ test, chạy một lượt
# nhỏ trên tập phát triển với đủ 15 hệ thống, rồi in bảng so sánh với B1.
#
#   ./run_quick.sh                 # 5 workflow, 1 seed (khoảng 1 phút)
#   ./run_quick.sh 20              # 20 workflow
#   ./run_quick.sh 20 2            # 20 workflow, 2 seed
#   SKIP_TESTS=1 ./run_quick.sh    # bỏ qua bộ test
#
# Chỉ chạy trên tập phát triển: không mở niêm phong tập đánh giá, không ghi log mở niêm phong.
# Số liệu của lượt nhanh chỉ để kiểm tra pipeline chạy đúng, không phải kết quả.
set -euo pipefail

WORKFLOWS="${1:-5}"
SEEDS="${2:-1}"
FROZEN="freeze-v3: clean sha256:9c4c0d018b18"

ROOT="$(cd "$(dirname "$0")" && pwd)"
PY="$ROOT/.venv/bin/python"
cd "$ROOT"

step() { printf '\n== %s\n' "$*"; }

step "1/5 Môi trường"
if [[ ! -x "$PY" ]]; then
    command -v uv >/dev/null || { echo "Cần cài uv: https://docs.astral.sh/uv/"; exit 1; }
    uv sync
fi
"$PY" --version

cd "$ROOT/auditgame"

step "2/5 Bản đóng băng"
if [[ ! -f spikes/v3-table/v3_line5_table.npz ]]; then
    echo "Thiếu spikes/v3-table/v3_line5_table.npz (bảng dòng 5 của Sentinel)."
    exit 1
fi
HEADER="$("$PY" -m v3.freeze_v3 --header | tail -1)"
echo "$HEADER"
if [[ "$HEADER" != "$FROZEN"* ]]; then
    echo "Mã không khớp bản đã ký ở Gate 4 (cần: $FROZEN)."
    exit 1
fi

step "3/5 Bộ test v3"
if [[ "${SKIP_TESTS:-0}" == 1 ]]; then
    echo "bỏ qua (SKIP_TESTS=1)"
else
    "$PY" tests/run_v3.py | tail -6
fi

step "4/5 Lượt chạy nhỏ trên dev: $WORKFLOWS workflow, $SEEDS seed, ô headline"
OUT="spikes/v3-run/quick-$(date +%Y%m%d-%H%M%S)"
"$PY" tools/v3_run.py --split dev --blocks main --headline \
    --workflows "$WORKFLOWS" --seeds "$SEEDS" --out "$OUT" \
    --systems "B1 audit-at-commit" "B2 uniform random" "B3 audit-on-insertion" \
              "B4 audit-on-retrieval" "B5 risk-score" "B6 two-stage" "cost-greedy" \
              "SW randomised" "Oracle (+)" "Sentinel" "Sentinel [dhat=oracle]" \
              "Sentinel -randomization" "Sentinel -alarm memory" "Sentinel -benign-drift" \
              "Sentinel -transition uncertainty" \
    || echo "(v3_run.py thoát khác 0: control chưa đạt, xem $OUT/summary.json)"

step "5/5 Bảng so sánh với B1"
"$PY" tools/quick_summary.py "$OUT"
echo "Bản ghi và summary.json: auditgame/$OUT"
