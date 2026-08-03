#!/usr/bin/env bash
# Builds a hostile Karpathy-style vault and asserts the five migration guarantees.
#
#   ./tests/test-migration.sh
#
# Every check is POSITIVE where it can be: it is not enough that nothing bad happened,
# the tool must be shown to have actually done something. A test that passes when the
# script never ran is worse than no test at all.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="${TMPDIR:-/tmp}/g2-test-vault"
PASS=0; FAIL=0
ok(){ echo "  ✓ $1"; PASS=$((PASS+1)); }
no(){ echo "  ✗ $1"; FAIL=$((FAIL+1)); }

# ── preflight ────────────────────────────────────────────────────────────────
# Without these, every "nothing changed" assertion below would pass for the wrong
# reason. Fail loudly instead.
command -v python3 >/dev/null 2>&1 || { echo "python3 not found."; exit 2; }
if ! python3 -c "import yaml" >/dev/null 2>&1; then
  cat <<'MSG'
PyYAML is not installed, so nothing here can run.

  pip3 install pyyaml

If that fails with "externally-managed-environment" (common on macOS with
Homebrew or a system Python), pick one:

  pip3 install --user pyyaml
  pip3 install --break-system-packages pyyaml
  python3 -m venv .venv && . .venv/bin/activate && pip install pyyaml

MSG
  exit 2
fi
command -v git >/dev/null 2>&1 || { echo "git not found."; exit 2; }

# ── fixture: a deliberately hostile vault ────────────────────────────────────
rm -rf "$V"; mkdir -p "$V"/wiki/{summaries,people,topics}
cat > "$V/wiki/index.md" <<'EOF'
# Index
- [[Attention Is All You Need]]
EOF
cat > "$V/wiki/summaries/Attention Is All You Need.md" <<'EOF'
---
title: Attention Is All You Need
date: 2025-11-03
tags: [paper, nlp]
---
# Attention Is All You Need
Introduced [[Transformers]]. By [[Ashish Vaswani]].
```yaml
# fenced block mentioning [[Not A Real Page]] must be ignored
```
EOF
# no frontmatter at all; CJK, emoji, trailing spaces, no final newline
printf '# Transformers\n\nFrom [[Attention Is All You Need]].\n\n\xe6\xa0\xb8\xe5\xbf\x83 idea \xf0\x9f\xa7\xa0 acentos: funci\xc3\xb3n.\ntrailing spaces here   \nno final newline' > "$V/wiki/topics/Transformers.md"
cat > "$V/wiki/people/Ashish Vaswani.md" <<'EOF'
---
title: Ashish Vaswani
type: entity
relations:
  - predicate: "author_of"
    target: "[[Attention Is All You Need]]"
---
First author of [[Attention Is All You Need]].
EOF
cat > "$V/wiki/topics/Broken.md" <<'EOF'
---
title: Broken
tags: [a, b
badly: : indented
---
Invalid YAML. Must be skipped and left untouched.
EOF

git -C "$V" init -q
git -C "$V" config user.name t; git -C "$V" config user.email t@t
git -C "$V" add -A >/dev/null; git -C "$V" commit -qm base >/dev/null
BASE="$(git -C "$V" rev-parse HEAD)"

echo "LLM Wiki G² — migration guarantees"
echo

# ── 1. dry run ───────────────────────────────────────────────────────────────
echo "1. dry run writes nothing"
python3 "$REPO/bin/migrate.py" --vault "$V" >/dev/null 2>&1
DRY_RC=$?
[ $DRY_RC -eq 0 ] && ok "dry run exited cleanly" || no "dry run exited $DRY_RC"
[ -f "$V/.g2/migration-report.md" ] && ok "dry run produced a report (it really ran)" \
  || no "no report — the script did not run"
[ -z "$(git -C "$V" diff --name-only)" ] && ok "no page modified" || no "pages were modified"

# ── 5. git guard ─────────────────────────────────────────────────────────────
echo "5. git guard"
rm -rf "$V/.g2"
echo dirt > "$V/wiki/topics/dirty.md"
OUT="$(python3 "$REPO/bin/migrate.py" --vault "$V" --apply 2>&1)"
if [ $? -ne 0 ] && echo "$OUT" | grep -q "uncommitted changes"; then
  ok "refuses to apply on a dirty tree, for the right reason"
else
  no "dirty-tree guard did not fire as expected"
fi
rm -f "$V/wiki/topics/dirty.md"

# ── apply ────────────────────────────────────────────────────────────────────
echo "apply"
if python3 "$REPO/bin/migrate.py" --vault "$V" --apply --backup >/dev/null 2>&1; then
  ok "applied"
else
  no "apply failed"
fi
# positive: the scaffolding must actually be present now
if grep -q 'derivation_depth' "$V/wiki/topics/Transformers.md" \
   && grep -q 'derivation_depth' "$V/wiki/summaries/Attention Is All You Need.md"; then
  ok "scaffolding is present in the migrated pages"
else
  no "pages were not scaffolded — apply did nothing"
fi
[ -d "$V/.g2/backup" ] && ok "backup written" || no "no backup directory"

# ── 2. body invariant ────────────────────────────────────────────────────────
echo "2. body invariant"
python3 - "$V" "$BASE" <<'PY'
import subprocess, hashlib, sys
V, BASE = sys.argv[1], sys.argv[2]
def body(t):
    if t.startswith("---\n"):
        e = t.find("\n---\n", 3)
        if e != -1: return t[e+5:]
    return t
files = [f for f in subprocess.run(["git","-C",V,"ls-files","*.md"],
         capture_output=True, text=True).stdout.split("\n") if f.strip()]
bad = []
for f in files:
    b = subprocess.run(["git","-C",V,"show",f"{BASE}:{f}"],capture_output=True,text=True).stdout
    a = open(f"{V}/{f}", encoding="utf-8").read()
    if hashlib.sha256(body(b).encode()).hexdigest() != hashlib.sha256(body(a).encode()).hexdigest():
        bad.append(f)
if not files:
    print("  ✗ no files to compare"); sys.exit(1)
print(f"  ✓ {len(files)} bodies byte-identical" if not bad
      else "  ✗ bodies changed: " + ", ".join(bad))
sys.exit(1 if bad else 0)
PY
[ $? -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

# ── 3. additive only ─────────────────────────────────────────────────────────
echo "3. additive only"
if python3 "$REPO/bin/migrate.py" --vault "$V" --verify 2>&1 | grep -q "confined to the frontmatter"; then
  ok "verify: changes confined to added keys"
else
  no "verify found foreign changes"
fi
grep -q 'badly' "$V/wiki/topics/Broken.md" && ok "unparseable page left untouched" \
  || no "unparseable page was altered"

# ── 4. idempotent ────────────────────────────────────────────────────────────
echo "4. idempotent"
git -C "$V" add -A >/dev/null 2>&1; git -C "$V" commit -qm after >/dev/null 2>&1
python3 "$REPO/bin/migrate.py" --vault "$V" --apply >/dev/null 2>&1
CHANGED="$(git -C "$V" diff --name-only -- 'wiki/*.md' 'wiki/**/*.md')"
[ -z "$CHANGED" ] && ok "second run leaves every page untouched" \
  || no "second run changed: $CHANGED"

# ── graph builds ─────────────────────────────────────────────────────────────
echo "graph builds"
if python3 "$REPO/bin/build-edges.py" --vault "$V" --quiet >/dev/null 2>&1 \
   && [ -f "$V/edges.json" ] \
   && [ "$(python3 -c "import json;print(json.load(open('$V/edges.json'))['stats']['nodes'])")" -gt 0 ]; then
  ok "build-edges produced a non-empty graph"
else
  no "build-edges failed or produced nothing"
fi

echo
echo "  $PASS passed, $FAIL failed"
rm -rf "$V"
exit $((FAIL > 0))
