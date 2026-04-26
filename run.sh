#!/usr/bin/env bash
# PR-Gauntlet (py) — local scoring + submission helper
#
# Fix bugs in app/ using any tool, then:
#
#   bash run.sh           # score all 20 issues
#   bash run.sh 1         # score a single issue
#   bash run.sh --submit  # push branch + open PR against v1-bugged
#
# Branch is auto-named arena-<github-username> so competitors never collide.

set -euo pipefail

REPO_DIR="$(git rev-parse --show-toplevel)"
cd "$REPO_DIR"

# ── helpers ────────────────────────────────────────────────────────────────────
get_filter() {
    case $1 in
        1)  echo "create_status";;       2)  echo "page_offset";;
        3)  echo "search_case";;         4)  echo "delete_status";;
        5)  echo "websocket_unsubscribe";;6)  echo "retry_check";;
        7)  echo "ws_close";;            8)  echo "schedule_order";;
        9)  echo "audit_typo";;          10) echo "min_length";;
        11) echo "semaphore_leak";;      12) echo "naive_datetime";;
        13) echo "dep_eligibility";;     14) echo "event_type";;
        15) echo "step_status";;         16) echo "chain_flush";;
        17) echo "chain_list";;          18) echo "chain_run";;
        19) echo "chain_step";;          20) echo "chain_schedule";;
        *)  echo "ERROR: unknown issue $1" >&2; exit 1;;
    esac
}

get_slug() {
    # Prefer GitHub username; fall back to git user; last resort: hostname+timestamp
    if command -v gh &>/dev/null && gh auth status &>/dev/null 2>&1; then
        gh api user --jq .login 2>/dev/null && return
    fi
    git config user.name 2>/dev/null \
        | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed 's/-$//' \
        && return
    echo "$(hostname | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-')-$(date +%s | tail -c 6)"
}

ensure_branch() {
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$branch" == "v1-bugged" ]]; then
        local slug arena_branch
        slug=$(get_slug)
        arena_branch="arena-${slug}"
        echo "Creating branch: $arena_branch"
        git checkout -b "$arena_branch"
    fi
}

score_all() {
    if ! python -c "import httpx, pytest" 2>/dev/null; then
        echo "Installing scoring deps..."
        pip install pytest httpx -q
    fi
    python -m pytest scoring/test_issues.py -v --tb=short 2>&1 \
        | tee /tmp/prg_score_out.txt
    echo ""
    echo "── Score ───────────────────────────────────────────────────────────"
    python3 scoring/scorer.py < /tmp/prg_score_out.txt \
        | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"Fixed:       {d['fixed']}/20\")
print(f\"Base score:  {d['baseScore']}/100\")
print(f\"Chain bonus: +{d['chainBonus']}  (issues 16-20 share a root cause)\")
print(f\"FINAL:       {d['finalScore']}/110\")
"
}

score_one() {
    local num=$1 filter
    filter=$(get_filter "$num")
    if ! python -c "import httpx, pytest" 2>/dev/null; then
        pip install pytest httpx -q
    fi
    python -m pytest "scoring/test_issues.py::test_$(printf '%02d' "$num")_$filter" -v --tb=short
}

submit() {
    local branch
    branch=$(git rev-parse --abbrev-ref HEAD)
    if [[ "$branch" == "v1-bugged" ]]; then
        echo "ERROR: still on v1-bugged — run 'bash run.sh' first to create your arena branch"
        exit 1
    fi
    if ! git diff --quiet || ! git diff --cached --quiet; then
        git add -A -- ':!**/__pycache__' ':!*.pyc'
        git commit -m "arena: submission"
    fi
    git push origin "$branch"
    gh pr create \
        --repo "$(gh repo view --json nameWithOwner -q .nameWithOwner)" \
        --base v1-bugged \
        --head "$branch" \
        --title "Arena: $branch" \
        --body "Submitted via run.sh — CI will score and post results."
}

# ── dispatch ───────────────────────────────────────────────────────────────────
case "${1:-}" in
    --submit) submit;;
    "")       ensure_branch; score_all;;
    --help)
        grep '^#' "$0" | sed 's/^# *//'
        ;;
    *)
        ensure_branch
        for arg in "$@"; do
            score_one "$arg"
        done
        ;;
esac
