#!/usr/bin/env bash
# PR-Gauntlet (py) — local scoring helper
#
# Use this to check your score locally before submitting a PR.
# Fix the bugs in app/ using your tool of choice, then run:
#
#   bash run.sh           # score all 20 issues
#   bash run.sh 1         # score a single issue
#   bash run.sh 1 5 16    # score specific issues
#
# Submit: push your branch and open a PR against v1-bugged.
# CI will run the full score and post results as a PR comment.

set -euo pipefail

REPO_DIR="$(git rev-parse --show-toplevel)"
cd "$REPO_DIR"

# Install scoring deps if needed
if ! python -c "import httpx, pytest" 2>/dev/null; then
    echo "Installing scoring dependencies..."
    pip install pytest httpx -q
fi

if [[ $# -eq 0 ]]; then
    # Full run — score all 20 and print summary
    python -m pytest scoring/test_issues.py -v --tb=short 2>&1 \
        | tee /tmp/prg_score_output.txt
    echo ""
    echo "── Score ──────────────────────────────────────────────────────────"
    python3 scoring/scorer.py < /tmp/prg_score_output.txt \
        | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"Fixed:       {d['fixed']}/20\")
print(f\"Base score:  {d['baseScore']}/100\")
print(f\"Chain bonus: +{d['chainBonus']} (issues 16-20 share a root cause)\")
print(f\"FINAL:       {d['finalScore']}/110\")
"
else
    # Score specific issues
    for NUM in "$@"; do
        case $NUM in
            1)  F="create_status";;       2)  F="page_offset";;
            3)  F="search_case";;         4)  F="delete_status";;
            5)  F="websocket_unsubscribe";;6)  F="retry_check";;
            7)  F="ws_close";;            8)  F="schedule_order";;
            9)  F="audit_typo";;          10) F="min_length";;
            11) F="semaphore_leak";;      12) F="naive_datetime";;
            13) F="dep_eligibility";;     14) F="event_type";;
            15) F="step_status";;         16) F="chain_flush";;
            17) F="chain_list";;          18) F="chain_run";;
            19) F="chain_step";;          20) F="chain_schedule";;
            *) echo "Unknown issue: $NUM"; exit 1;;
        esac
        python -m pytest "scoring/test_issues.py::test_$(printf '%02d' "$NUM")_$F" -v --tb=short
    done
fi
