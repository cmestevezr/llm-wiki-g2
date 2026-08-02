---
name: g2-migrate
description: Safely upgrade an existing Karpathy-style LLM Wiki to G² without losing anything. Two phases - a script adds frontmatter scaffolding with a byte-identical body guarantee, then an LLM types the candidate edges. Triggers on "migrate my wiki", "upgrade without losing", "add a graph to my existing vault", "g2 migration".
---

# g2-migrate — upgrade without losing anything

The user has a working LLM Wiki. It may be months of accumulated notes. Your job is to add
structure **on top of it** without touching what is already there.

Treat their prose as immutable. You are adding frontmatter and nothing else.

## The promise you are keeping

`migrate.py` enforces five guarantees. Say them out loud to the user, because "safe
migration" means nothing without specifics:

1. **Dry run by default** — nothing is written without `--apply`
2. **Body invariant** — every page body stays byte-identical; verified after writing,
   and the run aborts and restores everything if it isn't
3. **Additive only** — existing frontmatter keys are never modified or removed
4. **Idempotent** — running twice changes nothing the second time
5. **Git guarded** — refuses to apply on a dirty tree

## Phase 1 — scaffolding (script, zero risk)

```bash
python3 bin/migrate.py --vault "$VAULT"                    # dry run
```

Then **show the user the report** at `.g2/migration-report.md`. Walk them through:

- how many pages will be touched, and which are skipped
- what fields get added and why each one earns its place
- the candidate edges found in their prose
- anything with unparseable frontmatter — those are skipped, not fixed

Get explicit consent. Then:

```bash
python3 bin/migrate.py --vault "$VAULT" --apply --backup
python3 bin/migrate.py --vault "$VAULT" --verify
python3 bin/build-edges.py --vault "$VAULT"
python3 bin/wq.py --vault "$VAULT" lint
```

If they get cold feet at any point: `git checkout -- .` puts everything back.

## Phase 2 — typing the edges (LLM, batched)

Phase 1 leaves every page with `relations: []`. The graph does not exist yet. This phase
builds it — and it is the one that costs tokens, so run it the cheap way.

The script deliberately does not guess predicates. It cannot tell `contradicts` from
`qualifies`; that is a semantic judgement and it belongs to a model or a person.

**How to run it:**

1. Get the candidates: `python3 bin/wq.py --vault "$VAULT" undeclared --min-count 1`
2. Work in **batches of 20–30 pages**, not one at a time.
3. For each batch, read only the frontmatter and the first ~300 words of each page — that
   is enough to type an edge, and it is a tenth of the cost of reading the whole page.
4. Propose `relations` blocks. Use only the 14 predicates in the vault's `CLAUDE.md`.
5. **Show the user each batch before writing.** They know their notes better than you do.
6. After each batch: `python3 bin/build-edges.py --vault "$VAULT"` and commit.

**Cost rules for this phase** — it is high-volume mechanical work:

- Cheap model, low effort. This is pattern matching, not reasoning.
- Keep the schema and instructions as an identical cached prefix; put the variable page
  text last.
- Batch API if the vault is large. Nobody is waiting on a backfill.
- Do not flip effort mid-session: it is part of the cache key.

## Phase 3 — anchoring (optional, ongoing)

```bash
python3 bin/wq.py --vault "$VAULT" unanchored
```

Pages whose provenance ends at another wiki page rather than at a raw source are not
anchored. Fill in `sources:` and `derivation_depth:` as you revisit them. This is
maintenance, not a migration step — do not block on it.

## What to tell the user at the end

- Their prose is byte-identical. `--verify` proves it, and git shows the diff.
- The graph is now derived, not maintained: `build-edges.py` regenerates it from the pages.
- Retrieval changed: `wq.py context` instead of reading the index.
- `edges.json` is derived — it should be gitignored.

## Never

- Rewrite, reword, reformat or reorganise their prose.
- Move or rename files as part of the migration. Offer it separately, afterwards.
- Overwrite their `CLAUDE.md`. Append a marked section, or write `CLAUDE.g2.md` and let
  them merge.
- Declare an edge you are not confident about. An unsure edge is worse than a missing one:
  the missing one shows up in `undeclared`, the wrong one is invisible.
