# LLM Wiki G²

> **G** for Graph · **G** for Git

Turn an [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) into a
derived knowledge graph. Edges are **declared while writing**, not extracted while reading.
Retrieval cost stops growing with the vault. Nothing you already wrote is touched.

```
LLM Wiki   ← Karpathy's pattern: prose that compounds
+ Graph    ← edges declared in frontmatter, L0/L1/L2 retrieval
+ Git      ← restore points and a time machine for evaluation
```

---

## The idea

Every knowledge-graph pipeline assumes the corpus is **someone else's text** that you must
extract entities and relations from. That assumption is where its problems come from: the
extractor reads later, with less context than the author had, and in
[Anthropic's own evaluation](https://platform.claude.com/cookbook/capabilities-knowledge-graph-guide)
recovers **0.38–0.55** of the entities.

In a second brain that assumption is simply false. **You control the writing step.** The
model writing the page already has the source open and the vault as context — it is the
best-placed observer in the system. Asking it to also emit its edges into frontmatter costs
a few dozen tokens on a write you were paying for anyway.

|  | Extraction | Declaration |
|---|---|---|
| When | later, in a separate pass | while writing, same pass |
| Who | an extractor with partial context | the author, with full context |
| Recall | 0.38–0.55, measured | ≈1.0 by construction |
| Over-merge | a real risk | not applicable |
| Graph/text drift | possible | impossible — there is one artefact |

The graph is not a parallel store. It is a **view derived from the frontmatter by a
script** — no LLM, no tokens, nothing that can diverge.

---

## What it buys you

| Operation | Plain LLM Wiki | LLM Wiki G² |
|---|---|---|
| Connection question | index + N pages | `edges.json`, **0 tokens** |
| Normal query | whole index + 5–10 pages | L0 → L1 → L2 |
| Find contradictions | O(n²) LLM pass | **O(1)** query |
| Find stale claims | heuristic lint | query over `valid_from` |
| Query cost as vault grows | superlinear | ≈ flat |

Measured on a real 28-node vault: frontmatter costs **23%** of what bodies cost, and
filtering L0→L1 saved **89–94%** against reading the same neighbourhood.

Karpathy notes the index pattern works "surprisingly well at moderate scale (~100 sources)".
That ceiling is a **token** ceiling, not a disk one — and it is the one this removes.

---

## Two ways in

### You have nothing yet

```bash
claude plugin marketplace add cmestevezr/llm-wiki-g2
claude plugin install llm-wiki-g2@llm-wiki-g2-marketplace
```

Open Claude in your (empty) vault folder and type `/g2`. It scaffolds the structure, installs
the scripts, sets up git and the Obsidian colours, and asks you one question: what is this
vault for. → [`docs/from-scratch.md`](docs/from-scratch.md)

### You already have an LLM Wiki

This is the case the project is built around. Your notes may be months of work; the
migration treats them as immutable.

```bash
python3 bin/migrate.py --vault ~/my-wiki            # dry run, writes a report
# read .g2/migration-report.md, then:
python3 bin/migrate.py --vault ~/my-wiki --apply --backup
python3 bin/migrate.py --vault ~/my-wiki --verify
```

Or just say **"upgrade my wiki"** to Claude and it follows the same path with you.
→ [`docs/migrating.md`](docs/migrating.md)

**Five guarantees, each one tested** ([`tests/test-migration.sh`](tests/test-migration.sh)):

1. **Dry run by default** — nothing is written without `--apply`
2. **Body invariant** — every page body stays byte-identical. Verified after writing; if it
   ever fails, the run aborts and restores every file it touched
3. **Additive only** — existing frontmatter keys are never modified or removed
4. **Idempotent** — running twice changes nothing the second time
5. **Git guarded** — refuses to apply on a dirty tree, so the migration is one clean diff

The migration deliberately **does not guess predicates**. A script cannot tell `contradicts`
from `qualifies`. It reports candidate edges found in your existing prose and leaves the
typing to you, or to a cheap batched LLM pass.

---

## Usage

```bash
python3 bin/build-edges.py              # after any write to wiki/
python3 bin/wq.py context "Page"        # L1: frontmatter of the neighbourhood
python3 bin/wq.py contradictions        # O(1)
python3 bin/wq.py stale --days 90
python3 bin/wq.py unanchored
python3 bin/wq.py lint                  # only this deserves LLM tokens
python3 bin/snapshot.sh "1 month ago"   # mount last month's vault
```

Full list in [`bin/README.md`](bin/README.md).

---

## Three ideas worth stealing even if you skip the rest

**Declared edges.** The graph falls out of the frontmatter instead of being extracted from
prose. Recall ≈1.0 instead of 0.38–0.55, and no second artefact to keep in sync.

**Anchors and drift.** Every page in a mature second brain was written by an LLM reading
pages written by an LLM. Errors do not get corrected along the way; they get consolidated,
and each rewrite makes them sound more confident. A vault that has drifted and one that has
compounded well **feel identical from the inside** — both give coherent, well-cross-referenced
answers. Internal coherence is not evidence of correctness. That is what the immutable
`.raw/` layer, `derivation_depth` and `wq.py unanchored` are for.

**Explicit frontier.** Gaps are nodes, not intuition. A vault that tracks what it does not
know can direct research instead of improvising it.

---

## Skills

Installed with the plugin, for Claude Code and Cowork:

| Skill | Triggers on |
|---|---|
| `g2-setup` | "set up g2", "/g2", "upgrade my wiki" |
| `g2-migrate` | "migrate my wiki", "upgrade without losing anything" |
| `g2-ingest` | "ingest this", "add this to the wiki" |
| `g2-query` | "what do you know about", "query the wiki" |
| `g2-lint` | "lint the wiki", "wiki health check" |

---

## Design notes

[`docs/design.md`](docs/design.md) has the full argument: where the idea comes from, what it
costs, what it does **not** solve, and three falsifiable predictions — including the one that
would sink it. If L0→L1→L2 answers worse than reading bodies, prose matters more than this
design assumes.

## Requirements

```bash
pip3 install pyyaml
```

Python 3.8+, PyYAML, git. On macOS, if pip refuses with
`externally-managed-environment`, use `pip3 install --user pyyaml` or a venv.

Obsidian is optional but assumed. Model-agnostic — nothing here depends on a particular
provider.

```bash
bash tests/run-all.sh           # 31 passed, 0 failed
```

Tested against Python 3.9 and 3.11. Two suites: `test-migration.sh` covers the five
guarantees, `test-queries.sh` covers every `wq.py` command with assertions on output
rather than exit codes.

## Credit

Built on Andrej Karpathy's
[LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) pattern,
Agrici Daniel's [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian), and
Anthropic's
[knowledge graph cookbook](https://platform.claude.com/cookbook/capabilities-knowledge-graph-guide).

MIT.
