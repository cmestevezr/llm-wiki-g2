#!/usr/bin/env bash
# Exercises every wq.py command against a fixture with known answers.
#
#   ./tests/test-queries.sh
#
# Asserts on OUTPUT, not on exit codes. A command that exits 0 while printing
# nothing useful is the failure mode this suite exists to catch.
set -uo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
V="${TMPDIR:-/tmp}/g2-query-vault"
PASS=0; FAIL=0
ok(){ echo "  ✓ $1"; PASS=$((PASS+1)); }
no(){ echo "  ✗ $1"; FAIL=$((FAIL+1)); }
# assert <label> <expected-substring> <command...>
assert(){ local l="$1" e="$2"; shift 2
  local out; out="$("$@" 2>&1)"
  if printf '%s' "$out" | grep -qF -- "$e"; then ok "$l"
  else no "$l — expected to find: $e"; printf '%s\n' "$out" | head -6 | sed 's/^/      /'; fi }

command -v python3 >/dev/null 2>&1 || { echo "python3 not found."; exit 2; }
python3 -c "import yaml" >/dev/null 2>&1 || { echo "PyYAML not installed. pip3 install pyyaml"; exit 2; }

# ── fixture with known answers ───────────────────────────────────────────────
rm -rf "$V"; mkdir -p "$V"/wiki/{sources,concepts,gaps}
cat > "$V/wiki/sources/Old Source.md" <<'EOF'
---
type: source
title: "Old Source"
valid_from: 2020-01-01
superseded_by: null
derivation_depth: 0
status: solid
aliases: ["OS", "the old one"]
relations:
  - predicate: "defines"
    target: "[[Some Concept]]"
sources: []
---
Body mentioning [[Some Concept]] twice: [[Some Concept]].
And an undeclared link to [[Floating Idea]].
EOF
cat > "$V/wiki/concepts/Some Concept.md" <<'EOF'
---
type: concept
title: "Some Concept"
valid_from: 2026-08-01
superseded_by: null
derivation_depth: 1
status: seed
aliases: []
relations:
  - predicate: "contradicts"
    target: "[[Old Source]]"
sources:
  - "[[Old Source]]"
---
Body of Some Concept.
EOF
cat > "$V/wiki/concepts/Floating Idea.md" <<'EOF'
---
type: concept
title: "Floating Idea"
valid_from: 2026-08-01
superseded_by: "[[Some Concept]]"
derivation_depth: 4
status: seed
aliases: []
relations:
  - predicate: "competes_with"
    target: "[[Some Concept]]"
sources: []
---
Unanchored on purpose: depth 4, no sources.
EOF
cat > "$V/wiki/gaps/Missing Source.md" <<'EOF'
---
type: gap
title: "Missing Source"
valid_from: 2026-08-01
superseded_by: null
derivation_depth: 0
status: open
aliases: []
relations:
  - predicate: "qualifies"
    target: "[[Some Concept]]"
sources: []
---
A declared hole.
EOF

echo "LLM Wiki G² — query layer"
echo

python3 "$REPO/bin/build-edges.py" --vault "$V" --quiet >/dev/null 2>&1 \
  && ok "graph builds" || no "build-edges failed"

W=(python3 "$REPO/bin/wq.py" --vault "$V")

echo "L0"
assert "contradictions finds the declared one" "Some Concept" "${W[@]}" contradictions
assert "gaps lists the open gap"               "Missing Source" "${W[@]}" gaps
assert "stale catches the 2020 claim"          "Old Source"     "${W[@]}" stale --days 30
assert "hubs reports in-degree"                "Some Concept"   "${W[@]}" hubs
assert "unanchored flags depth 4 / no sources" "Floating Idea"  "${W[@]}" unanchored
assert "undeclared surfaces the prose-only link" "Floating Idea" "${W[@]}" undeclared --min-count 1
assert "neighbors walks the graph"             "Some Concept"   "${W[@]}" neighbors "Old Source" --depth 2
assert "path finds a route"                    "hops"           "${W[@]}" path "Old Source" "Floating Idea"

echo "L1"
assert "context prints frontmatter"            "Some Concept"   "${W[@]}" context "Some Concept"
assert "context reports the L1/L2 tradeoff"    "L1 spent"       "${W[@]}" context "Some Concept"
assert "context flags a superseded page"       "SUPERSEDED"     "${W[@]}" context "Floating Idea" --depth 1

echo "resolution and reporting"
assert "alias resolves to the page"            "Old Source"     "${W[@]}" neighbors "the old one"
assert "substring resolves"                    "Old Source"     "${W[@]}" neighbors "Old Sou"
assert "stats counts epistemic edges"          "epistemic edges" "${W[@]}" stats
# The fixture contains one deliberate defect: Floating Idea is reachable only from
# prose, never from a declared edge. Asserting the lint FINDS a known defect is a
# stronger test than asserting it finds none — the latter passes on a broken lint.
assert "lint detects the planted orphan"       "Floating Idea"   "${W[@]}" lint
assert "lint counts it"                        "Total defects: 1" "${W[@]}" lint

echo "no Obsidian required"
# The README promises a vault is just a folder of markdown. The fixture above never
# creates .obsidian/, so every check so far already ran without it — assert it plainly
# so the promise is guarded rather than incidental.
[ ! -d "$V/.obsidian" ] && ok "the whole suite ran with no .obsidian directory" \
  || no ".obsidian was created — the docs claim it is not needed"
assert "queries work on a plain markdown folder" "nodes" "${W[@]}" stats

echo "failure modes"
OUT="$("${W[@]}" neighbors "Nonexistent Page" 2>&1)"
printf '%s' "$OUT" | grep -q "Not found" && ok "unknown page fails clearly" \
  || no "unknown page did not produce a clear error"
OUT="$(python3 "$REPO/bin/wq.py" --vault "${TMPDIR:-/tmp}/definitely-not-a-vault" stats 2>&1)"
printf '%s' "$OUT" | grep -q "build-edges" && ok "missing edges.json points at the fix" \
  || no "missing edges.json gave no guidance"

echo
echo "  $PASS passed, $FAIL failed"
rm -rf "$V"
exit $((FAIL > 0))
