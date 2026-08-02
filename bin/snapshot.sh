#!/usr/bin/env bash
# snapshot.sh — mount a past state of the vault next to the current one.
#
# This is the controlled comparison for "is my wiki actually getting better, or am
# I just getting better at asking?". Answer the same gold set against today's vault
# and against the vault from a month ago, same model, same settings. The operator
# and the model are constant across both branches; only the graph differs.
#
# Usage:
#   bin/snapshot.sh --list           commits available
#   bin/snapshot.sh "1 month ago"    mount that state
#   bin/snapshot.sh a1b2c3d          mount a specific commit
#   bin/snapshot.sh --clean          unmount
set -euo pipefail

VAULT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${TMPDIR:-/tmp}/g2-snapshot"
cd "$VAULT"

case "${1:-}" in
  --list|"")
    echo "Commits available:"; git log --date=short --format="  %h  %ad  %s"; exit 0 ;;
  --clean)
    git worktree remove --force "$DEST" 2>/dev/null || true
    rm -rf "$DEST"; git worktree prune; echo "✓ snapshot unmounted"; exit 0 ;;
esac

REF="$1"
if ! git rev-parse --verify "$REF^{commit}" >/dev/null 2>&1; then
  REF="$(git rev-list -1 --before="$1" HEAD || true)"
  [ -n "$REF" ] || { echo "No commits before '$1'"; exit 1; }
fi

git worktree remove --force "$DEST" 2>/dev/null || true
rm -rf "$DEST"
git worktree add --detach -q "$DEST" "$REF"

echo "✓ snapshot at: $DEST"
echo "  commit: $(git log -1 --format='%h  %ad  %s' --date=short "$REF")"
echo
python3 "$VAULT/bin/build-edges.py" --vault "$DEST" --quiet
printf "\n  %-10s %-8s %-10s %s\n" "" "nodes" "edges" "body tokens"
for pair in "today:$VAULT" "snapshot:$DEST"; do
  python3 - "${pair%%:*}" "${pair#*:}/edges.json" <<'PY'
import json, sys
label, p = sys.argv[1], sys.argv[2]
try: s = json.load(open(p, encoding="utf-8"))["stats"]
except Exception: print(f"  {label:<10} (no edges.json)"); raise SystemExit
print(f"  {label:<10} {s['nodes']:<8} {s['edges_declared']:<10} ~{s['body_tokens_total']}")
PY
done
echo
echo "Now run the same gold set against both:"
echo "  python3 bin/wq.py --vault \"$VAULT\" context \"<Page>\""
echo "  python3 bin/wq.py --vault \"$DEST\" context \"<Page>\""
echo "When done:  bin/snapshot.sh --clean"
