---
name: g2-lint
description: Health-check an LLM Wiki G² vault - broken links, orphans, pages without relations, stale claims, unanchored provenance, vocabulary violations. Runs the script first and spends LLM tokens only on what it flags. Triggers on "lint the wiki", "wiki health check", "audit the vault", "find orphans", "clean up the wiki".
---

# g2-lint — let the script find it, then think about it

The point of this skill is restraint. Most of a health check is mechanical and should cost
zero tokens. Run the script, then reason **only** over what it flags.

## Step 1 — the free part

```bash
python3 bin/build-edges.py --vault "$VAULT"
python3 bin/wq.py --vault "$VAULT" lint
python3 bin/wq.py --vault "$VAULT" stale --days 90
python3 bin/wq.py --vault "$VAULT" unanchored
python3 bin/wq.py --vault "$VAULT" undeclared --min-count 2
python3 bin/wq.py --vault "$VAULT" gaps
python3 bin/wq.py --vault "$VAULT" hubs
```

That covers broken links, invalid frontmatter, predicates outside the vocabulary, pages
with no relations, orphans, expired claims, unanchored provenance and candidate edges.
None of it costs a token.

## Step 2 — the part that needs judgement

Only now, and only on what the script surfaced:

- **Candidate edges** — type the ones that are real. A script cannot tell `contradicts`
  from `qualifies`.
- **Undeclared contradictions** — the script only finds *declared* ones. Pages that
  `competes_with` each other, or two sources with `supports` edges to opposite claims, are
  worth reading. This is the single highest-value thing an LLM lint pass does.
- **Concepts mentioned but with no page** — recurring terms in prose that never became a node.
- **Over-merged or duplicated entities** — two pages for one thing. Check `aliases`.
- **High `derivation_depth` with no `sources`** — the drift candidates. Re-anchor them
  against `.raw/`.

## Step 3 — report, do not silently fix

Write the findings to `wiki/meta/` as a `session` note, or show them in chat. **Ask before
editing.** A lint pass that quietly rewrites pages is indistinguishable from data loss.

Exception: obviously safe repairs — a broken wikilink where the target was clearly renamed
— can be offered as a batch for one-shot approval.

## On hubs

`wq.py hubs` shows in-degree concentration. If the top 10 nodes hold most of the edges, the
vault is hub-shaped, and the useful work is consolidating those hubs rather than adding
nodes. Growth in node count is not the same thing as growth in usefulness, and only one of
them is easy to measure.

## A caution worth repeating to the user

A vault that has drifted and a vault that has compounded well feel identical from the
inside. Both produce coherent, well-cross-referenced answers. Internal coherence is not
evidence of correctness — that is what `unanchored` is for, and why `.raw/` is immutable.
