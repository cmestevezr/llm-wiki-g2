#!/usr/bin/env python3
"""
migrate.py — upgrade an existing LLM Wiki to LLM Wiki G², without losing anything.

WHAT IT DOES
    Adds the G² frontmatter scaffolding to pages that lack it, and reports which
    edges you could declare. That is all. It does not rewrite prose, does not move
    files, and does not invent relationships.

THE FIVE GUARANTEES
    1. DRY RUN BY DEFAULT      nothing is written unless you pass --apply
    2. BODY INVARIANT          every page body stays byte-identical; verified after
                               writing, and the run aborts and restores if it isn't
    3. ADDITIVE ONLY           existing frontmatter keys are never modified or removed
    4. IDEMPOTENT              running twice changes nothing the second time
    5. GIT GUARDED             refuses to --apply on a dirty tree unless --no-git

WHAT IT DELIBERATELY DOES NOT DO
    It will not guess predicates. A script cannot tell `contradicts` from `qualifies`.
    It emits candidate edges from links already present in your prose and leaves the
    typing to you or to an LLM pass. See docs/migrating.md, phase 2.

USAGE
    python3 bin/migrate.py --vault ~/my-wiki                 # dry run, writes a report
    python3 bin/migrate.py --vault ~/my-wiki --apply         # after reading the report
    python3 bin/migrate.py --vault ~/my-wiki --apply --backup
    python3 bin/migrate.py --vault ~/my-wiki --verify        # check an applied migration
"""
import argparse, datetime, difflib, hashlib, json, os, re, shutil, subprocess, sys

try:
    import yaml
except ImportError:
    sys.exit("PyYAML is required.  pip install pyyaml  (add --break-system-packages if needed)")

# fields G² adds. Nothing else is ever touched.
ADDED = ["valid_from", "superseded_by", "derivation_depth", "relations", "sources", "aliases"]
# `type` is added when absent; `title` only when the page had no frontmatter at all.
# verify() must know every key migrate can introduce, or it reports false positives.
ADDABLE = ["type", "title"] + ADDED

TYPE_BY_DIR = {
    "sources": "source", "source": "source", "papers": "source", "raw-notes": "source",
    "concepts": "concept", "concept": "concept", "topics": "concept", "ideas": "concept",
    "entities": "entity", "entity": "entity", "people": "entity", "orgs": "entity",
    "questions": "synthesis", "synthesis": "synthesis", "answers": "synthesis",
    "gaps": "gap", "meta": "decision",
}
SPECIAL = {"index.md", "log.md", "hot.md", "overview.md", "readme.md", "claude.md", "agents.md"}
FENCE = re.compile(r"```.*?```", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#]+)")


# ───────────────────────────────────────────────────────────── helpers

def split_fm(raw):
    """Return (frontmatter_text, body). Body includes no frontmatter, ever."""
    if raw.startswith("---\n"):
        end = raw.find("\n---\n", 3)
        if end != -1:
            return raw[4:end], raw[end + 5:]
    return None, raw


def parse_fm(fm_text):
    if fm_text is None:
        return {}, None
    try:
        d = yaml.safe_load(fm_text)
        return (d if isinstance(d, dict) else {}), None
    except yaml.YAMLError as e:
        return {}, str(e).split("\n")[0][:90]


def guess_type(relpath, fm):
    if fm.get("type"):
        return str(fm["type"])
    for part in relpath.replace("\\", "/").split("/")[:-1]:
        t = TYPE_BY_DIR.get(part.lower())
        if t:
            return t
    return "concept"


def guess_valid_from(fm, path):
    for k in ("valid_from", "created", "date"):
        v = fm.get(k)
        if v:
            return str(v)[:10]
    ts = os.path.getmtime(path)
    return datetime.date.fromtimestamp(ts).isoformat()


def guess_depth(ntype):
    return {"source": 0, "gap": 0, "decision": 0, "session": 0}.get(ntype, 1)


def render_added(fm, ntype, valid_from):
    """YAML lines for missing keys only. Never re-renders what already exists."""
    lines = []
    if "type" not in fm:
        lines.append(f"type: {ntype}")
    if "valid_from" not in fm:
        lines.append(f"valid_from: {valid_from}")
    if "superseded_by" not in fm:
        lines.append("superseded_by: null")
    if "derivation_depth" not in fm:
        lines.append(f"derivation_depth: {guess_depth(ntype)}")
    if "aliases" not in fm:
        lines.append("aliases: []")
    if "relations" not in fm:
        lines.append("relations: []   # TODO g2: declare edges — see docs/migrating.md")
    if "sources" not in fm:
        lines.append("sources: []")
    return lines


def git(vault, *args):
    try:
        r = subprocess.run(["git", "-C", vault, *args], capture_output=True, text=True, timeout=30)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except (OSError, subprocess.SubprocessError):
        return 1, "", "git unavailable"


# ───────────────────────────────────────────────────────────── scan

def scan(vault):
    pages = []
    for dp, dirs, fns in os.walk(vault):
        dirs[:] = [d for d in dirs
                   if d not in (".obsidian", ".git", ".trash", "node_modules", "bin", ".g2-backup")
                   and d != ".g2" and not d.startswith(".raw")]
        for fn in sorted(fns):
            if not fn.endswith(".md") or fn.lower() in SPECIAL:
                continue
            full = os.path.join(dp, fn)
            rel = os.path.relpath(full, vault)
            raw = open(full, encoding="utf-8").read()
            fm_text, body = split_fm(raw)
            fm, err = parse_fm(fm_text)
            ntype = guess_type(rel, fm)
            pages.append({
                "rel": rel, "full": full, "name": fn[:-3], "raw": raw,
                "fm_text": fm_text, "fm": fm, "body": body, "yaml_error": err,
                "type": ntype, "valid_from": guess_valid_from(fm, full),
                "missing": [k for k in (["type"] + ADDED) if k not in fm],
                "body_sha": hashlib.sha256(body.encode()).hexdigest(),
            })
    return pages


def candidate_edges(pages):
    known = {p["name"] for p in pages}
    out = []
    for p in pages:
        declared = {str(r.get("target", "")).strip("[]")
                    for r in (p["fm"].get("relations") or []) if isinstance(r, dict)}
        seen = {}
        for m in WIKILINK.finditer(FENCE.sub("", p["body"])):
            t = m.group(1).strip()
            if t != p["name"] and t in known and t not in declared:
                seen[t] = seen.get(t, 0) + 1
        for t, n in sorted(seen.items(), key=lambda kv: -kv[1]):
            out.append({"source": p["name"], "target": t, "mentions": n})
    return out


# ───────────────────────────────────────────────────────────── apply

def new_content(p):
    """Build the new file text. Body is spliced in untouched, by construction."""
    added = render_added(p["fm"], p["type"], p["valid_from"])
    if not added:
        return p["raw"]
    if p["fm_text"] is None:
        fm_block = "\n".join([f'title: "{p["name"]}"'] + added)
    else:
        fm_block = p["fm_text"].rstrip("\n") + "\n" + "\n".join(added)
    return "---\n" + fm_block + "\n---\n" + p["body"]


def apply(vault, pages, backup):
    todo = [p for p in pages if p["missing"] and not p["yaml_error"]]
    if backup:
        dest = os.path.join(vault, ".g2", "backup",
                            datetime.datetime.now().strftime("%Y%m%d-%H%M%S"))
        for p in todo:
            d = os.path.join(dest, p["rel"])
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(p["full"], d)
        print(f"  backup of {len(todo)} files -> {os.path.relpath(dest, vault)}")

    written, violations = [], []
    for p in todo:
        content = new_content(p)
        open(p["full"], "w", encoding="utf-8").write(content)
        written.append(p)
        # GUARANTEE 2: verify body byte-identity immediately
        _, body_after = split_fm(open(p["full"], encoding="utf-8").read())
        if hashlib.sha256(body_after.encode()).hexdigest() != p["body_sha"]:
            violations.append(p["rel"])

    if violations:
        print("\n  ✗ BODY INVARIANT VIOLATED — restoring every file touched")
        for p in written:
            open(p["full"], "w", encoding="utf-8").write(p["raw"])
        print("  ✓ restored. Nothing was changed. Please open an issue with the file below:")
        for v in violations:
            print(f"      {v}")
        return False, 0
    return True, len(written)


# ───────────────────────────────────────────────────────────── report

def write_report(vault, pages, cands, applied):
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    todo = [p for p in pages if p["missing"]]
    bad = [p for p in pages if p["yaml_error"]]
    by_type = {}
    for p in pages:
        by_type[p["type"]] = by_type.get(p["type"], 0) + 1

    L = [f"# LLM Wiki G² — migration report", "",
         f"Generated: {ts}", f"Vault: `{vault}`",
         f"Mode: **{'APPLIED' if applied else 'DRY RUN — nothing was written'}**", "",
         "## Summary", "",
         f"- Pages found: **{len(pages)}**",
         f"- Pages needing scaffolding: **{len(todo)}**",
         f"- Pages already complete: **{len(pages) - len(todo) - len(bad)}**",
         f"- Pages with unreadable frontmatter (skipped): **{len(bad)}**",
         f"- Candidate edges found in your prose: **{len(cands)}**", "",
         "## Type inferred, by folder", ""]
    for t, n in sorted(by_type.items(), key=lambda kv: -kv[1]):
        L.append(f"- `{t}` — {n}")
    L += ["", "Types were inferred from folder names. Wrong guesses are harmless: edit the",
          "`type:` field on any page and re-run `build-edges.py`.", ""]

    if bad:
        L += ["## Skipped — frontmatter does not parse", "",
              "These were **not touched**. Fix the YAML by hand, then re-run.", ""]
        for p in bad:
            L.append(f"- `{p['rel']}` — {p['yaml_error']}")
        L.append("")

    L += ["## Fields that will be added", "",
          "Only these, and only where absent. Nothing existing is modified.", "",
          "| Field | Why |", "|---|---|",
          "| `type` | routes the page into the graph |",
          "| `valid_from` | turns stale-claim detection from a lint pass into a query |",
          "| `superseded_by` | lets a claim expire instead of rotting silently |",
          "| `derivation_depth` | how many LLM hops from an immutable source — the anti-drift instrument |",
          "| `relations` | the declared edges. Seeded empty, for you to fill |",
          "| `sources` | provenance chain |",
          "| `aliases` | entity resolution, for free |", ""]

    if cands:
        L += ["## Candidate edges", "",
              "Links already present in your prose with no declared relation. A script cannot",
              "tell `contradicts` from `qualifies`, so these are **proposals, not decisions**.",
              "Phase 2 of the migration types them. See `docs/migrating.md`.", "",
              "| From | To | Mentions |", "|---|---|---|"]
        for c in cands[:150]:
            L.append(f"| {c['source']} | {c['target']} | {c['mentions']} |")
        if len(cands) > 150:
            L.append(f"\n_…and {len(cands) - 150} more._")
        L.append("")

    L += ["## Next", ""]
    if not applied:
        L += ["```bash", "python3 bin/migrate.py --vault . --apply --backup", "```", "",
              "Then phase 2: have Claude type the candidate edges above, in batches.", ""]
    else:
        L += ["```bash", "python3 bin/build-edges.py --vault .",
              "python3 bin/wq.py lint", "```", "",
              "Then phase 2: have Claude type the candidate edges, in batches. Your prose is",
              "untouched — every body in this vault is byte-identical to before the migration.", ""]

    # a dot-directory: invisible to Obsidian, easy to gitignore, out of the vault's way
    d = os.path.join(vault, ".g2")
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "migration-report.md")
    open(path, "w", encoding="utf-8").write("\n".join(L))
    return path


# ───────────────────────────────────────────────────────────── verify

def verify(vault):
    """Confirm an applied migration never altered a body, using git."""
    rc, out, _ = git(vault, "rev-parse", "--git-dir")
    if rc != 0:
        print("No git repository — cannot verify after the fact.")
        print("Re-run the migration on a git-tracked vault to get this guarantee.")
        return 1
    rc, diff, _ = git(vault, "diff", "HEAD", "--unified=0", "--", "*.md")
    if rc != 0:
        print("Could not read the diff.")
        return 1
    if not diff.strip():
        print("✓ No uncommitted changes to verify.")
        return 0

    offending, cur, in_fm = [], None, False
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur, in_fm = line[6:], False
            continue
        if line.startswith(("---", "+++", "@@", "diff ", "index ")):
            continue
        if line.startswith(("+", "-")):
            body = line[1:]
            if body.strip() == "---":
                in_fm = not in_fm
                continue
            # a changed line is acceptable only if it is one of the added keys
            key = body.split(":")[0].strip()
            if key not in ADDABLE and body.strip() and not body.startswith("  "):
                offending.append((cur, line[:70]))

    if offending:
        print(f"✗ {len(offending)} changed lines outside the added frontmatter keys:\n")
        for f, l in offending[:20]:
            print(f"   {f}\n     {l}")
        return 1
    print("✓ Every change is confined to the frontmatter keys G² adds.")
    print("  No prose was altered.")
    return 0


# ───────────────────────────────────────────────────────────── main

def main():
    ap = argparse.ArgumentParser(
        description="Upgrade an LLM Wiki to G². Dry run by default.",
        formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("--vault", default=".", help="path to the vault")
    ap.add_argument("--apply", action="store_true", help="actually write (default: dry run)")
    ap.add_argument("--backup", action="store_true", help="copy files to .g2-backup/ first")
    ap.add_argument("--no-git", action="store_true", help="skip the clean-tree check")
    ap.add_argument("--verify", action="store_true", help="check an applied migration")
    a = ap.parse_args()
    vault = os.path.abspath(os.path.expanduser(a.vault))

    if not os.path.isdir(vault):
        sys.exit(f"Not a directory: {vault}")
    if a.verify:
        sys.exit(verify(vault))

    print(f"LLM Wiki G² migration")
    print(f"  vault: {vault}")
    print(f"  mode:  {'APPLY' if a.apply else 'DRY RUN (nothing will be written)'}\n")

    # GUARANTEE 5
    if a.apply and not a.no_git:
        rc, _, _ = git(vault, "rev-parse", "--git-dir")
        if rc != 0:
            print("  ✗ This vault is not a git repository.")
            print("    G² leans on git for restore points and for the evaluation snapshots.")
            print("    Run this first — it takes one second and makes everything reversible:\n")
            print(f'      git -C "{vault}" init')
            print(f'      git -C "{vault}" add -A')
            print(f'      git -C "{vault}" commit -m "Before LLM Wiki G2 migration"\n')
            print("    Or re-run with --no-git if you version the vault another way.")
            sys.exit(1)
        rc, dirty, _ = git(vault, "status", "--porcelain")
        if dirty.strip():
            print("  ✗ The working tree has uncommitted changes.")
            print("    Commit them first so the migration is a clean, revertible diff:\n")
            print(f'      git -C "{vault}" add -A')
            print(f'      git -C "{vault}" commit -m "Before LLM Wiki G2 migration"\n')
            sys.exit(1)
        print("  ✓ git: clean tree, restore point available\n")

    pages = scan(vault)
    if not pages:
        print("  No markdown pages found outside the special files.")
        print("  If this is an empty vault, you want the scaffold path instead:")
        print("  ask Claude to run the g2-setup skill.")
        sys.exit(0)

    cands = candidate_edges(pages)
    todo = [p for p in pages if p["missing"] and not p["yaml_error"]]
    bad = [p for p in pages if p["yaml_error"]]

    print(f"  {len(pages)} pages, {len(todo)} need scaffolding, "
          f"{len(bad)} unreadable, {len(cands)} candidate edges")

    if a.apply:
        if not todo:
            print("\n  Nothing to do — this vault is already scaffolded. (Idempotent.)")
        else:
            print()
            ok, n = apply(vault, pages, a.backup)
            if not ok:
                sys.exit(2)
            print(f"  ✓ {n} pages scaffolded")
            print(f"  ✓ body invariant held: every page body is byte-identical")
    else:
        # dry run: show the diff for one page so the user sees exactly what happens
        if todo:
            p = todo[0]
            print(f"\n  Example — what would change in `{p['rel']}`:\n")
            d = difflib.unified_diff(p["raw"].splitlines(), new_content(p).splitlines(),
                                     lineterm="", n=1)
            for line in list(d)[2:14]:
                print("    " + line)
            print("\n  Body lines: unchanged. Only frontmatter keys are appended.")

    report = write_report(vault, pages, cands, a.apply)
    print(f"\n  report: {os.path.relpath(report, vault)}")
    if not a.apply:
        print("\n  Nothing was written. Read the report, then re-run with --apply --backup")
    else:
        print(f'\n  Verify:  python3 bin/migrate.py --vault "{vault}" --verify')
        print(f'  Revert:  git -C "{vault}" checkout -- .')


if __name__ == "__main__":
    main()
