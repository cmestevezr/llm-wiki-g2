#!/usr/bin/env bash
# Builds a hostile Karpathy-style vault and asserts the five migration guarantees.
#   ./tests/test-migration.sh
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="${TMPDIR:-/tmp}/g2-test-vault"
PASS=0; FAIL=0
ok(){ echo "  ✓ $1"; PASS=$((PASS+1)); }
no(){ echo "  ✗ $1"; FAIL=$((FAIL+1)); }

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
  - predicate: "autor_de"
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

git -C "$V" init -q; git -C "$V" config user.name t; git -C "$V" config user.email t@t
git -C "$V" add -A; git -C "$V" commit -q -m base
BASE="$(git -C "$V" rev-parse HEAD)"

echo "LLM Wiki G² — migration guarantees"
echo

echo "1. dry run writes nothing"
python3 "$REPO/bin/migrate.py" --vault "$V" >/dev/null 2>&1
[ -z "$(git -C "$V" diff --name-only)" ] && ok "no page modified" || no "pages were modified"

echo "5. git guard"
git -C "$V" checkout -q -- . ; rm -rf "$V/.g2"
echo dirt > "$V/wiki/topics/dirty.md"
python3 "$REPO/bin/migrate.py" --vault "$V" --apply >/dev/null 2>&1
[ $? -ne 0 ] && ok "refuses to apply on a dirty tree" || no "applied on a dirty tree"
rm -f "$V/wiki/topics/dirty.md"

echo "apply"
python3 "$REPO/bin/migrate.py" --vault "$V" --apply --backup >/dev/null 2>&1 \
  && ok "applied" || no "apply failed"

echo "2. body invariant"
python3 - "$V" "$BASE" <<'PY'
import subprocess,hashlib,sys
V,BASE=sys.argv[1],sys.argv[2]
def body(t):
    if t.startswith("---\n"):
        e=t.find("\n---\n",3)
        if e!=-1: return t[e+5:]
    return t
bad=[]
files=[f for f in subprocess.run(["git","-C",V,"ls-files","*.md"],capture_output=True,text=True).stdout.split("\n") if f.strip()]
for f in files:
    b=subprocess.run(["git","-C",V,"show",f"{BASE}:{f}"],capture_output=True,text=True).stdout
    a=open(f"{V}/{f}",encoding="utf-8").read()
    if hashlib.sha256(body(b).encode()).hexdigest()!=hashlib.sha256(body(a).encode()).hexdigest():
        bad.append(f)
print(("  ✓ %d bodies byte-identical"%len(files)) if not bad else ("  ✗ bodies changed: "+", ".join(bad)))
sys.exit(1 if bad else 0)
PY
[ $? -eq 0 ] && PASS=$((PASS+1)) || FAIL=$((FAIL+1))

echo "3. additive only"
python3 "$REPO/bin/migrate.py" --vault "$V" --verify >/dev/null 2>&1 \
  && ok "verify: changes confined to added keys" || no "verify found foreign changes"

grep -q 'badly' "$V/wiki/topics/Broken.md" && ok "unparseable page left untouched" \
  || no "unparseable page was altered"

echo "4. idempotent"
git -C "$V" add -A >/dev/null; git -C "$V" commit -q -m after
python3 "$REPO/bin/migrate.py" --vault "$V" --apply >/dev/null 2>&1
CHANGED="$(git -C "$V" diff --name-only -- 'wiki/*.md' 'wiki/**/*.md')"
[ -z "$CHANGED" ] && ok "second run leaves every page untouched" \
  || no "second run changed: $CHANGED"

echo "graph builds"
python3 "$REPO/bin/build-edges.py" --vault "$V" --quiet >/dev/null 2>&1 \
  && ok "build-edges runs on the migrated vault" || no "build-edges failed"

echo
echo "  $PASS passed, $FAIL failed"
rm -rf "$V"
exit $((FAIL > 0))
