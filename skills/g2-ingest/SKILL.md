---
name: g2-ingest
description: Ingest a source into an LLM Wiki G² vault - read it, write the source page, update affected concepts and entities, and declare typed edges while writing. Triggers on "ingest", "ingest this", "process this source", "add this to the wiki", "read and file this", "batch ingest".
---

# g2-ingest — declare the edges while you write

The difference between G² and a plain LLM Wiki lives in this operation. You are not just
writing pages; you are declaring the graph as you go, because right now — with the source
in front of you and the vault as context — you are the best-placed observer in the system.

An extractor reading this page three weeks from now will have strictly less context. That
is why its recall is 0.38–0.55 and yours is close to 1.0.

## Before you start

Cheap model, **low effort**. Extraction is mechanical. Save the reasoning budget for query
sessions — and do not flip effort mid-session, it is part of the cache key.

Read the vault's `CLAUDE.md` for the predicate vocabulary. Use only those predicates.

## Sequence

1. **Read the source** from `.raw/`. If the user handed you a URL, fetch it and save a copy
   to `.raw/` first — the raw layer is the anchor, and an anchor you did not keep is not
   an anchor.

2. **Check what exists first.** Do not create a duplicate concept page under a different
   name. This costs almost nothing:
   ```bash
   python3 bin/wq.py --vault "$VAULT" stats
   python3 bin/wq.py --vault "$VAULT" neighbors "<likely related page>" --depth 2
   ```

3. **Write the source page** in `wiki/sources/` with `derivation_depth: 0`. Include what
   the source actually claims, and — this matters — what you find weak in it. A source page
   that only summarises is worth less than one that also argues.

4. **Update the affected concepts and entities.** A single source typically touches 8–15
   pages. Declare edges on each one as you write it.

5. **Declare `contradicts` whenever you notice a clash.** This is the highest-value thing
   you do all session. An undeclared contradiction turns into a silently wrong answer
   later, and nobody will ever find it — the O(n²) lint pass that would catch it is exactly
   the pass that stops being run once the vault is big.

6. **Update `wiki/index.md`**, prepend to `wiki/log.md`.

7. **Rebuild and check:**
   ```bash
   python3 bin/build-edges.py --vault "$VAULT"
   python3 bin/wq.py --vault "$VAULT" lint
   ```

8. **Commit:** `git add -A && git commit -m "ingest | <Source Title>"`

## Declaring edges well

- **Outgoing only.** If B already declares the relation, A does not repeat it.
- **5–7 per page, ceiling.** More than that and the frontmatter stops being cheap to read,
  which kills the L1 layer that makes the whole design work.
- **Every page gets at least one.** `relations: []` is a defect.
- **Prefer epistemic predicates.** `supports`, `contradicts`, `qualifies`, `competes_with`
  are what make the graph worth traversing. A vault of nothing but `part_of` and
  `derives_from` is a filing cabinet, not a knowledge graph.
- **When unsure, leave it undeclared.** It will surface in `wq.py undeclared` as a
  candidate. A missing edge is visible; a wrong edge is not.

## Batch ingestion

Several sources at once: extract them **in parallel**, then do a single cross-referencing
pass at the end. Cross-referencing before all the sources are in produces edges you will
have to revise.

For a large backlog, use the Batch API. It is the textbook case: high volume, not
time-sensitive, identical prefix. Nobody is waiting on a backfill.

## Declare the gaps too

If the source raises a question it does not answer, or you relied on something you could
not verify, create a `wiki/gaps/` page. A vault that tracks its own frontier can direct
research instead of improvising it — and it costs one file.
