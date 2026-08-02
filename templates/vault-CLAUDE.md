# LLM Wiki G² — vault schema

**G** for Graph · **G** for Git.
An LLM Wiki whose graph is declared at write time and whose every claim chains back to
an immutable source.

> Adapt this file. It is meant to co-evolve with you — that is the point of the schema
> layer. Keep it static *within* a session, though: it is your cached prefix.

## Guiding principle

> **Don't extract what you can declare.**
> The markdown page is the single source of truth. The graph is **derived** from its
> frontmatter by script, with no LLM in the loop. There are not two artefacts that can
> drift apart: there is one, and its views.

## Layers

- `.raw/` — original sources. **Immutable.** The agent reads, never writes here.
  These are the system's anchors.
- `wiki/` — generated pages. The agent owns this layer entirely.
- `bin/` — deterministic scripts. They derive views; they never write to `wiki/`.
- `CLAUDE.md` — this file. Stable, cacheable prefix.

| Folder | Type | Contents |
|---|---|---|
| `wiki/sources/` | `source` | One page per ingested source |
| `wiki/concepts/` | `concept` | Ideas, patterns, techniques |
| `wiki/entities/` | `entity` | People, organisations, tools |
| `wiki/questions/` | `synthesis` | Answers, comparisons, proposals |
| `wiki/gaps/` | `gap` | What the vault does **not** know |
| `wiki/meta/` | `decision`, `session` | Decisions and session records |

Special files: `wiki/index.md`, `wiki/log.md` (prepend), `wiki/hot.md`, `wiki/overview.md`,
`edges.json` (derived — never edit, never commit).

---

## Predicate vocabulary — CLOSED SET

Every declared relation uses **exactly one** of these 14. Do not invent predicates. If none
fits, use the nearest and note it in `log.md` so the vocabulary can be revised deliberately.

**Structural**

| Predicate | A —pred→ B means |
|---|---|
| `derives_from` | A comes from B (page ← source, idea ← origin) |
| `defines` | A introduces or defines B |
| `implements` | A is a concrete implementation of B |
| `part_of` | A is a component of B |
| `author_of` | A (person/org) created B |
| `uses` | A employs B as a tool or dependency |

**Epistemic** — these are what make the graph worth reasoning over

| Predicate | A —pred→ B means |
|---|---|
| `supports` | A is evidence for B |
| `contradicts` | A clashes with B. **Declare it whenever you notice it** |
| `qualifies` | A limits B's scope without negating it |
| `supersedes` | A replaces B |
| `competes_with` | A and B are rival explanations of the same thing |
| `solves` | A solves the problem stated in B |
| `improves` | A is an improvement over B |

**Discursive**

| Predicate | A —pred→ B means |
|---|---|
| `compares` | A contrasts B with others without taking sides |

`mentions` is reserved: the script generates it for prose links with no declared relation.
Never write it by hand.

### Declaration rules

- **Outgoing edges only.** Never declare the inverse: if B declares it, A does not repeat it.
- **Ceiling of 5–7 edges per page.** Above that the frontmatter stops being cheap to read,
  which defeats the L1 layer.
- Every page needs **at least one** relation. `relations: []` is a defect the lint reports.
- An undeclared `contradicts` is the worst defect in the vault: it turns a detectable
  contradiction into a silently wrong answer.

---

## Frontmatter

```yaml
---
type: <source|concept|entity|synthesis|gap|decision|session>
title: "Title"
created: YYYY-MM-DD
updated: YYYY-MM-DD
valid_from: YYYY-MM-DD          # when the main claim became valid
superseded_by: null             # "[[Page]]" once it expires
derivation_depth: 1             # LLM hops from .raw/ — 0 means direct quotation
tags: []
status: <seed|developing|solid>
aliases: []
relations:
  - predicate: "qualifies"
    target: "[[Exact Page Name]]"
related: []
sources: []                     # "[[source page]]" or a path in .raw/
---
```

`derivation_depth` is the anti-drift instrument. 0 is a direct quotation from `.raw/`.
Each synthesis-over-synthesis adds 1. High depth means the page is a candidate for
re-anchoring against the source.

---

## Retrieval protocol — L0 → L1 → L2

**Never read full pages before filtering through L0 and L1.**

| Level | What you read | Cost | Tool |
|---|---|---|---|
| **L0** | topology: predicates and targets | **0 LLM tokens** | `bin/wq.py` |
| **L1** | frontmatter of the candidates | ~60 tok/page | `bin/wq.py context` |
| **L2** | bodies of the finalists | ~1000 tok/page | `Read` |

```bash
python3 bin/wq.py neighbors "Page" --depth 2     # L0: who is nearby
python3 bin/wq.py context   "Page" --depth 2     # L1: frontmatter, budgeted
# L2: read only the 3-5 pages that survived
```

Queries that should **never** cost LLM tokens:

```bash
python3 bin/wq.py contradictions      # declared contradictions
python3 bin/wq.py stale --days 90     # claims past their review horizon
python3 bin/wq.py gaps                # open frontier
python3 bin/wq.py hubs                # central nodes
python3 bin/wq.py undeclared          # prose links with no edge -> candidates
python3 bin/wq.py unanchored          # claims with no chain to .raw/
```

`index.md` still exists for human navigation, but it is **no longer the retrieval
mechanism**. Do not read it whole during a query.

---

## Operations

- **Ingest** — read a source from `.raw/` → create a page in `wiki/sources/` with
  `derivation_depth: 0` → update the affected concepts and entities **declaring edges** →
  if anything clashes with what exists, declare `contradicts` → update `index.md` →
  prepend to `log.md` → run `bin/build-edges.py`.
- **Query** — `hot.md` → L0 → L1 → L2. Always cite the specific page.
- **Lint** — `bin/wq.py lint`. Follow with an LLM pass **only** over what the script flags.
- **Save** — file a conversation or analysis into `wiki/questions/`.

After any write to `wiki/`: **`python3 bin/build-edges.py`**.

---

## Versioning

The vault is a git repo. That buys history, a restore point, and a **time machine for
evaluation**.

```bash
git add -A && git commit -m "ingest | <Source Title>"
bin/snapshot.sh "1 month ago"    # mount the past state in a separate worktree
bin/snapshot.sh --clean
```

`snapshot.sh` exists so you can answer the same gold set against today's vault and against
last month's, with the same model and settings. It is the only thing that separates the
effect of the network from the effect of the operator getting better at asking.

Not versioned: `edges.json` (derived) and `.obsidian/workspace.json` (UI state).

---

## Cost rules

- Ingest and query in **separate sessions**. `effort` is part of the prompt-cache key;
  flipping it mid-session re-reads the whole context at full price.
- Ingest: cheap model, low effort. Extraction is mechanical work.
- Query, synthesis and contradiction detection: high effort.
- This file is static: send it as a **cached prefix**.
- Backfilling several sources: Batch API, never synchronous.
- Before spending tokens looking for something, check whether `bin/wq.py` already
  answers it for free.
