#!/usr/bin/env python3
"""
wq.py — L0/L1 queries over edges.json. Zero LLM tokens.

L0  topology     neighbors, path, contradictions, stale, hubs, gaps, undeclared
L1  frontmatter  context   (~60 tok/page)
L2  bodies       read them yourself, only for what survived L0/L1 (~1000 tok/page)

Usage:  python3 bin/wq.py <command> [args]
        python3 bin/wq.py --help
"""
import argparse, datetime, json, os, sys
from collections import defaultdict, deque

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_VAULT = os.path.dirname(HERE)
EPISTEMIC = {"supports", "contradicts", "qualifies", "supersedes",
             "competes_with", "solves", "improves"}
RECORD_TYPES = ("entity", "gap", "decision", "session")


def load(vault):
    p = os.path.join(vault, "edges.json")
    if not os.path.exists(p):
        sys.exit(f"No edges.json in {vault}\nRun first:  python3 bin/build-edges.py --vault {vault}")
    return json.load(open(p, encoding="utf-8"))


def resolve(g, name):
    """Exact name, alias, or unique substring."""
    if name in g["nodes"]:
        return name
    low = name.lower()
    for n, d in g["nodes"].items():
        if any(low == str(a).lower() for a in d.get("aliases", [])):
            return n
    hits = [n for n in g["nodes"] if low in n.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        sys.exit("Ambiguous. Candidates:\n  " + "\n  ".join(sorted(hits)))
    sys.exit(f"Not found: {name}")


def adjacency(g, declared_only=True):
    out, inn = defaultdict(list), defaultdict(list)
    for e in g["edges"]:
        if declared_only and e["origin"] != "declared":
            continue
        out[e["source"]].append(e)
        inn[e["target"]].append(e)
    return out, inn


def walk(g, start, depth, direction="both", declared_only=True):
    out, inn = adjacency(g, declared_only)
    seen, q = {start: 0}, deque([start])
    while q:
        cur = q.popleft()
        if seen[cur] >= depth:
            continue
        nxt = []
        if direction in ("out", "both"):
            nxt += [e["target"] for e in out[cur]]
        if direction in ("in", "both"):
            nxt += [e["source"] for e in inn[cur]]
        for n in nxt:
            if n not in seen and n in g["nodes"]:
                seen[n] = seen[cur] + 1
                q.append(n)
    return seen, out, inn


# ────────────────────────────────────────────────────────── commands

def cmd_neighbors(g, a):
    start = resolve(g, a.page)
    seen, out, inn = walk(g, start, a.depth, a.direction, not a.include_prose)
    print(f"Neighborhood of «{start}»  (depth {a.depth}, direction {a.direction})\n")
    for lvl in range(1, a.depth + 1):
        pages = sorted(n for n, d in seen.items() if d == lvl)
        if not pages:
            continue
        print(f"  hop {lvl} ({len(pages)}):")
        for n in pages:
            print(f"    {n:<48} [{g['nodes'][n]['type']}]")
        print()
    total = sum(g["nodes"][n]["body_tokens_est"] for n in seen)
    print(f"  {len(seen)} pages reached. Reading them all at L2 would cost ~{total} tokens.")
    print(f'  Cheap next step:  wq.py context "{start}" --depth {a.depth}')


def cmd_context(g, a):
    """L1 projection: frontmatter of the neighborhood, on a token budget."""
    start = resolve(g, a.page)
    seen, out, _ = walk(g, start, a.depth)
    order = sorted(seen, key=lambda n: (seen[n], -g["nodes"][n]["in_degree"]))
    used = 0
    print(f"# L1 context for «{start}»  (budget {a.budget} tokens)\n")
    for i, n in enumerate(order):
        d = g["nodes"][n]
        if used + d["fm_tokens_est"] > a.budget:
            print(f"\n[budget spent; {len(order) - i} pages omitted]")
            break
        used += d["fm_tokens_est"]
        sup = "  ⚠ SUPERSEDED" if d["superseded_by"] else ""
        print(f"## {n}   [{d['type']}/{d['status']}]  hop {seen[n]}  "
              f"valid_from {d['valid_from'] or '?'}{sup}")
        rels = [f"{e['predicate']} → {e['target']}" for e in out[n]]
        if rels:
            print("   " + "; ".join(rels))
        print(f"   (body ~{d['body_tokens_est']} tok)\n")
    full = sum(g["nodes"][n]["body_tokens_est"] for n in seen)
    print(f"---\nL1 spent ~{used} tok. Reading the same bodies at L2 would have cost ~{full} tok.")
    if not full:
        return
    if used >= full:
        print("\nL1 costs more than L2 here — your pages are still shorter than their")
        print("frontmatter. That is expected on a young vault: the protocol pays off once")
        print("bodies outweigh metadata, typically past a few dozen real pages.")
        print("Until then, just read the pages.")
    else:
        print(f"Saved by filtering: {100 - 100 * used // full}%")


def cmd_path(g, a):
    out, inn = adjacency(g)
    s, t = resolve(g, a.source), resolve(g, a.target)
    prev, q = {s: None}, deque([s])
    while q:
        cur = q.popleft()
        if cur == t:
            break
        for e in out[cur] + inn[cur]:
            n = e["target"] if e["source"] == cur else e["source"]
            if n not in prev and n in g["nodes"]:
                prev[n] = (cur, e)
                q.append(n)
    if t not in prev:
        print(f"No path between «{s}» and «{t}»")
        return
    chain, cur = [], t
    while prev[cur]:
        p, e = prev[cur]
        chain.append((p, e["predicate"], cur, e["source"] == p))
        cur = p
    print(f"Path «{s}» → «{t}»  ({len(chain)} hops)\n")
    for p, pred, c, fwd in reversed(chain):
        print(f"  {p}\n    --[{pred}]{'-->' if fwd else '<--'} {c}")


def cmd_contradictions(g, a):
    e = [x for x in g["edges"] if x["predicate"] == "contradicts"]
    print(f"Declared contradictions: {len(e)}\n")
    for x in e:
        print(f"  {x['source']}\n    ⚡ contradicts → {x['target']}\n")
    if not e:
        print("  (none)\n")
    print("This is O(1). Finding them by re-reading the vault with an LLM is O(n²)")
    print(f"and at {g['stats']['nodes']} nodes would cost ~{g['stats']['body_tokens_total']} "
          f"tokens per pass.")


def cmd_stale(g, a):
    today, rows = datetime.date.today(), []
    for n, d in g["nodes"].items():
        if not d["valid_from"]:
            continue
        try:
            age = (today - datetime.date.fromisoformat(d["valid_from"][:10])).days
        except ValueError:
            continue
        if age >= a.days:
            rows.append((age, n, d))
    rows.sort(reverse=True)
    print(f"Claims with valid_from {a.days}+ days old ({len(rows)}):\n")
    for age, n, d in rows:
        flag = "  [already superseded]" if d["superseded_by"] else ""
        print(f"  {age:>4}d  {n:<50} [{d['type']}]{flag}")
    if not rows:
        print("  (none)")


def cmd_hubs(g, a):
    rows = sorted(g["nodes"].items(), key=lambda kv: -kv[1]["in_degree"])[: a.top]
    tot = sum(d["in_degree"] for d in g["nodes"].values()) or 1
    print(f"Nodes by in-degree (declared edges). Total edges: {tot}\n")
    acc = 0
    for i, (n, d) in enumerate(rows, 1):
        acc += d["in_degree"]
        print(f"  {i:>2}. {d['in_degree']:>3} in / {d['out_degree']:>2} out   "
              f"{n:<44} cum {100 * acc // tot}%")
    print(f"\nIf the top {a.top} holds >60%, your vault is hub-shaped: work on the hubs,")
    print("not on node count.")


def cmd_undeclared(g, a):
    rows = sorted([e for e in g["edges"]
                   if e["origin"] == "prose" and e.get("count", 0) >= a.min_count],
                  key=lambda e: -e.get("count", 0))
    print(f"Prose links with no declared relation, {a.min_count}+ mentions ({len(rows)}):\n")
    for e in rows[: a.top]:
        print(f"  {e['count']}x  {e['source']}  →  {e['target']}")
    print("\nThese are candidate edges. They recover part of the serendipity that")
    print("declaration loses — at zero token cost.")


def cmd_unanchored(g, a):
    bad = []
    for n, d in g["nodes"].items():
        if d["type"] in ("source", "gap"):
            continue
        depth, has_src = d["derivation_depth"], bool(d["sources"])
        if not has_src or depth is None or (isinstance(depth, int) and depth > a.max_depth):
            why = []
            if not has_src:
                why.append("no sources")
            if depth is None:
                why.append("no derivation_depth")
            elif depth > a.max_depth:
                why.append(f"depth={depth}")
            bad.append((n, d, ", ".join(why)))
    print(f"Pages without a solid anchor to your raw sources ({len(bad)}):\n")
    for n, d, why in sorted(bad):
        print(f"  {n:<50} [{d['type']}]  {why}")
    print("\nA claim whose provenance ends at another wiki page, rather than at an")
    print("immutable source, is not anchored. Coherence is not evidence of correctness.")


def cmd_gaps(g, a):
    rows = [(n, d) for n, d in g["nodes"].items() if d["type"] == "gap"]
    print(f"Open frontier ({len(rows)} gaps):\n")
    for n, d in sorted(rows):
        print(f"  [{d['status']}] {n}")
    if not rows:
        print("  (none declared — a vault that tracks what it does not know")
        print("   can direct research instead of improvising it)")


def cmd_lint(g, a):
    print("=== LINT ===\n")
    by = defaultdict(list)
    for x in g["problems"]:
        by[x["kind"]].append(x)
    for k, v in sorted(by.items()):
        print(f"{k} ({len(v)}):")
        for x in v[:12]:
            print(f"   {x['page']}: {x['detail']}")
        print()
    no_out = [n for n, d in g["nodes"].items() if d["out_degree"] == 0]
    if no_out:
        print(f"pages_without_relations ({len(no_out)}):")
        for n in sorted(no_out):
            print(f"   {n}")
        print()
    orph = [n for n, d in g["nodes"].items()
            if d["in_degree"] == 0 and not (d["type"] in RECORD_TYPES and d["out_degree"] > 0)]
    if orph:
        print(f"orphans_no_inbound ({len(orph)}):")
        for n in sorted(orph):
            print(f"   {n}")
        print()
    total = len(g["problems"]) + len(no_out) + len(orph)
    print(f"Total defects: {total}")
    print("Only what appears here deserves an LLM pass. The rest is already verified.")


def cmd_stats(g, a):
    s = g["stats"]
    preds = defaultdict(int)
    for e in g["edges"]:
        if e["origin"] == "declared":
            preds[e["predicate"]] += 1
    print(f"Generated: {g['generated']}\n")
    print(f"  nodes             {s['nodes']}")
    print(f"  declared edges    {s['edges_declared']}")
    print(f"  prose links       {s['edges_prose']}")
    print(f"  problems          {s['problems']}\n")
    print(f"  body tokens       ~{s['body_tokens_total']}   (L2)")
    print(f"  frontmatter       ~{s['fm_tokens_total']}   (L1) = "
          f"{100 * s['fm_tokens_total'] // max(s['body_tokens_total'], 1)}% of bodies\n")
    epi = sum(v for k, v in preds.items() if k in EPISTEMIC)
    print(f"  epistemic edges   {epi}/{s['edges_declared']} "
          f"({100 * epi // max(s['edges_declared'], 1)}%)\n")
    for k, v in sorted(preds.items(), key=lambda kv: -kv[1]):
        print(f"   {'*' if k in EPISTEMIC else ' '} {k:<16} {v}")
    print("\n  (* epistemic — the edges that make the graph worth reasoning over)")


# ────────────────────────────────────────────────────────── CLI

def main():
    ap = argparse.ArgumentParser(description="L0/L1 queries over your vault. Zero LLM tokens.")
    ap.add_argument("--vault", default=DEFAULT_VAULT, help="vault path (default: repo root)")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("neighbors", help="topological neighborhood (L0)")
    p.add_argument("page"); p.add_argument("--depth", type=int, default=1)
    p.add_argument("--direction", choices=["in", "out", "both"], default="both")
    p.add_argument("--include-prose", action="store_true"); p.set_defaults(fn=cmd_neighbors)

    p = sub.add_parser("context", help="frontmatter of the neighborhood, budgeted (L1)")
    p.add_argument("page"); p.add_argument("--depth", type=int, default=2)
    p.add_argument("--budget", type=int, default=1500); p.set_defaults(fn=cmd_context)

    p = sub.add_parser("path", help="shortest path between two pages")
    p.add_argument("source"); p.add_argument("target"); p.set_defaults(fn=cmd_path)

    p = sub.add_parser("contradictions", help="declared contradictions"); p.set_defaults(fn=cmd_contradictions)

    p = sub.add_parser("stale", help="claims past their review horizon")
    p.add_argument("--days", type=int, default=90); p.set_defaults(fn=cmd_stale)

    p = sub.add_parser("hubs", help="central nodes")
    p.add_argument("--top", type=int, default=10); p.set_defaults(fn=cmd_hubs)

    p = sub.add_parser("undeclared", help="prose links with no edge: candidates")
    p.add_argument("--min-count", type=int, default=2)
    p.add_argument("--top", type=int, default=25); p.set_defaults(fn=cmd_undeclared)

    p = sub.add_parser("unanchored", help="claims with no chain to a raw source")
    p.add_argument("--max-depth", type=int, default=2); p.set_defaults(fn=cmd_unanchored)

    p = sub.add_parser("gaps", help="open frontier"); p.set_defaults(fn=cmd_gaps)
    p = sub.add_parser("lint", help="all defects"); p.set_defaults(fn=cmd_lint)
    p = sub.add_parser("stats", help="graph summary"); p.set_defaults(fn=cmd_stats)

    a = ap.parse_args()
    a.fn(load(os.path.abspath(os.path.expanduser(a.vault))), a)


if __name__ == "__main__":
    main()
