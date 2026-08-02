---
name: g2-query
description: Answer questions from an LLM Wiki G² vault using the L0-L1-L2 retrieval protocol, so retrieval cost stays flat as the vault grows. Triggers on "what do you know about", "query the wiki", "search the wiki", "what does my vault say about", "ask the wiki".
---

# g2-query — L0 → L1 → L2

**High effort** for this session. Query and synthesis are where judgement matters, and this
is the session type that justifies the cost. Keep ingestion in a different session.

## The rule

**Never read full pages before filtering through L0 and L1.**

Reading `index.md` and then opening ten pages is the old way. It works at 100 pages and
falls apart at 500, because the index grows with the vault while the answer does not.

| Level | What | Cost |
|---|---|---|
| L0 | topology — predicates and targets | **0 tokens** |
| L1 | frontmatter of the candidates | ~60 tok/page |
| L2 | bodies of the finalists | ~1000 tok/page |

## Sequence

1. **`hot.md`** — recent context, if it exists.

2. **L0: find the neighbourhood.** Zero tokens.
   ```bash
   python3 bin/wq.py --vault "$VAULT" neighbors "<Page>" --depth 2
   python3 bin/wq.py --vault "$VAULT" path "<A>" "<B>"
   ```

3. **L1: read frontmatter, budgeted.**
   ```bash
   python3 bin/wq.py --vault "$VAULT" context "<Page>" --depth 2 --budget 1500
   ```
   This prints each candidate's type, status, `valid_from`, declared edges and body size.
   It is usually enough to decide what to open.

4. **L2: read 3–5 bodies.** Only the ones that survived. Use `Read`.

5. **Answer with citations to specific pages.** Never from pretraining. If the vault does
   not know, say so — and offer to create a `gap` page.

## Before answering, check the cheap things

These cost nothing and change answers:

```bash
python3 bin/wq.py --vault "$VAULT" contradictions   # is this contested in the vault?
python3 bin/wq.py --vault "$VAULT" stale --days 90  # is the claim past its horizon?
```

If a relevant page has `superseded_by` set, or a `valid_from` old enough to matter, **say
so in the answer**. A confident synthesis built on expired claims reads exactly like a
correct one — that is the failure mode this vault is built to prevent.

## Check the anchoring on anything load-bearing

```bash
python3 bin/wq.py --vault "$VAULT" unanchored
```

If your answer leans on a page with high `derivation_depth` and no `sources`, flag it.
That claim has been through several rounds of LLM compression and nobody has re-checked it
against the original.

## File the answer back

A good answer should not vanish into chat history. If the question took real work — a
comparison, an analysis, a connection nobody had drawn — offer to save it to
`wiki/questions/` with its own declared edges. This is what makes explorations compound
the same way ingested sources do.

Use the `g2-save` conventions: `type: synthesis`, the original `question:` in the
frontmatter, `answer_quality:`, and honest `sources:`.
