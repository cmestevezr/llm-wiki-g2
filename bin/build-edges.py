#!/usr/bin/env python3
"""
build-edges.py — derive edges.json from the vault's frontmatter.

The graph is NOT extracted by reading pages with an LLM. It is derived from the
relations the author declared while writing. Deterministic, zero tokens, no drift.

Usage:  python3 bin/build-edges.py [--vault .] [--quiet]
Output: edges.json at the vault root. Derived — never edit, never commit.
"""
import argparse, json, os, re, sys, datetime

try:
    import yaml
except ImportError:
    sys.exit(
        "PyYAML is required.\n\n"
        "  pip3 install pyyaml\n\n"
        "If that fails with 'externally-managed-environment' (common on macOS with\n"
        "Homebrew or a system Python), pick one:\n\n"
        "  pip3 install --user pyyaml\n"
        "  pip3 install --break-system-packages pyyaml\n"
        "  python3 -m venv .venv && . .venv/bin/activate && pip install pyyaml\n"
    )

VOCAB = {
    "structural":  ["derives_from", "defines", "implements", "part_of", "author_of", "uses"],
    "epistemic":   ["supports", "contradicts", "qualifies", "supersedes", "competes_with",
                    "solves", "improves"],
    "discursive":  ["compares"],
}
ALL_PREDS = {p for g in VOCAB.values() for p in g}
FENCE = re.compile(r"```.*?```", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
CHARS_PER_TOKEN = 4  # rough, but consistent — good enough to compare retrieval paths


def split_frontmatter(raw):
    if not raw.startswith("---\n"):
        return {}, raw
    end = raw.find("\n---\n", 3)
    if end == -1:
        return {}, raw
    try:
        fm = yaml.safe_load(raw[4:end]) or {}
    except yaml.YAMLError as e:
        return {"__error__": str(e)[:120]}, raw[end + 5:]
    return (fm if isinstance(fm, dict) else {}), raw[end + 5:]


def scan(vault):
    nodes, edges, problems = {}, [], []
    for dp, dirs, fns in os.walk(vault):
        dirs[:] = [d for d in dirs if d not in (".obsidian", ".git", "node_modules", "bin")]
        for fn in sorted(fns):
            if not fn.endswith(".md"):
                continue
            path = os.path.relpath(os.path.join(dp, fn), vault)
            if fn in ("CLAUDE.md", "README.md", "index.md", "log.md", "hot.md", "overview.md"):
                continue  # documentation, not knowledge
            name = fn[:-3]
            raw = open(os.path.join(dp, fn), encoding="utf-8").read()
            fm, body = split_frontmatter(raw)
            if "__error__" in fm:
                problems.append({"page": name, "kind": "invalid_frontmatter", "detail": fm["__error__"]})
                fm = {}

            nodes[name] = {
                "path": path,
                "type": fm.get("type", "?"),
                "title": fm.get("title", name),
                "status": fm.get("status"),
                "valid_from": str(fm.get("valid_from")) if fm.get("valid_from") else None,
                "superseded_by": fm.get("superseded_by"),
                "derivation_depth": fm.get("derivation_depth"),
                "tags": fm.get("tags") or [],
                "aliases": fm.get("aliases") or [],
                "sources": fm.get("sources") or [],
                "body_tokens_est": len(body) // CHARS_PER_TOKEN,
                "fm_tokens_est": (len(raw) - len(body)) // CHARS_PER_TOKEN,
            }

            declared = set()
            for rel in (fm.get("relations") or []):
                if not isinstance(rel, dict):
                    problems.append({"page": name, "kind": "malformed_relation", "detail": str(rel)[:60]})
                    continue
                pred = (rel.get("predicate") or "").strip()
                tgt = (rel.get("target") or "").strip().strip("[]")
                if not pred or not tgt:
                    problems.append({"page": name, "kind": "incomplete_relation", "detail": str(rel)[:60]})
                    continue
                if pred not in ALL_PREDS:
                    problems.append({"page": name, "kind": "predicate_not_in_vocabulary",
                                     "detail": f"{pred} -> {tgt}"})
                declared.add(tgt)
                edges.append({"source": name, "predicate": pred, "target": tgt, "origin": "declared"})

            # prose links with no declared relation -> candidate edges (predicate "mentions")
            seen = {}
            for m in WIKILINK.finditer(FENCE.sub("", body)):
                t = m.group(1).strip()
                if t != name:
                    seen[t] = seen.get(t, 0) + 1
            for t, n in seen.items():
                if t not in declared:
                    edges.append({"source": name, "predicate": "mentions", "target": t,
                                  "origin": "prose", "count": n})
    return nodes, edges, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vault", default=".")
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()

    nodes, edges, problems = scan(a.vault)

    known = set(nodes)
    for e in edges:
        if e["target"] not in known:
            problems.append({"page": e["source"], "kind": "broken_link", "detail": e["target"]})

    for n in nodes.values():
        n["in_degree"] = n["out_degree"] = 0
    for e in edges:
        if e["origin"] != "declared":
            continue
        if e["source"] in nodes:
            nodes[e["source"]]["out_degree"] += 1
        if e["target"] in nodes:
            nodes[e["target"]]["in_degree"] += 1

    decl = [e for e in edges if e["origin"] == "declared"]
    out = {
        "generated": datetime.datetime.now().isoformat(timespec="seconds"),
        "vocabulary": VOCAB,
        "stats": {
            "nodes": len(nodes),
            "edges_declared": len(decl),
            "edges_prose": len(edges) - len(decl),
            "problems": len(problems),
            "body_tokens_total": sum(n["body_tokens_est"] for n in nodes.values()),
            "fm_tokens_total": sum(n["fm_tokens_est"] for n in nodes.values()),
        },
        "nodes": nodes,
        "edges": edges,
        "problems": problems,
    }
    dest = os.path.join(a.vault, "edges.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)

    if not a.quiet:
        s = out["stats"]
        print(f"edges.json -> {s['nodes']} nodes, {s['edges_declared']} declared edges, "
              f"{s['edges_prose']} prose links, {s['problems']} problems")
        print(f"  bodies ~{s['body_tokens_total']} tok | frontmatter ~{s['fm_tokens_total']} tok "
              f"({100*s['fm_tokens_total']//max(s['body_tokens_total'],1)}% of bodies)")


if __name__ == "__main__":
    main()
