# Why this exists

<p align="center">
  <img src="assets/graph-emergence.webp" width="100%"
       alt="A sheet of markdown seen at an angle. Its frontmatter lines peel off the top edge and stretch into luminous directed edges, resolving into a sparse graph of coloured nodes. A thin chain descends from the page toward an anchor out of frame." />
</p>

This project did not start as a project. It started as a comparison between three pieces of
work that were circulating in mid-2026, all of them good, none of them quite answering the
question the others raised. What follows is the argument that came out of putting them side
by side — what each one solves, what each one leaves open, and what a fourth thing has to do
to be worth building.

If you only read one section, read [What you actually get](#what-you-actually-get) and
[Who should not use this](#who-should-not-use-this).

---

## The three references

### Andrej Karpathy — [LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)

**The diagnosis, and it is the right one.** RAG makes the model rediscover knowledge from
scratch on every question; nothing accumulates. The alternative is a persistent wiki the LLM
builds and maintains, sitting between you and your raw sources. Knowledge gets compiled once
and kept current rather than re-derived per query.

The insight underneath is about labour, not retrieval: *the tedious part of a knowledge base
is not reading or thinking, it is the bookkeeping.* Humans abandon wikis because maintenance
grows faster than value. An LLM does not get bored and can touch fifteen files in one pass.

The gist is **deliberately abstract** — it says so. It communicates a pattern and expects
your agent to instantiate it. That is a feature, and it is why implementations exist. But it
means five things are left genuinely open:

| Open | Consequence |
|---|---|
| Retrieval is `index.md` → pages | Cost grows with the vault, not with the question |
| Contradictions found by a lint pass | O(n²) comparison; stops being run exactly when it matters |
| Stale claims found heuristically | You have to *hope* the model notices |
| No computable structure | Nothing about the wiki can be answered without spending tokens |
| Drift unaddressed | Every page is an LLM reading LLM pages, for months |

Karpathy names the first one himself: the index pattern works *"surprisingly well at moderate
scale (~100 sources, ~hundreds of pages)"*. That ceiling is real, and it is a **token**
ceiling, not a disk one.

### Agrici Daniel — [claude-obsidian](https://github.com/AgriciDaniel/claude-obsidian)

**The pattern made executable**, and a genuinely good contribution of its own: the **hot
cache** (`hot.md`), refreshed by session hooks so the next session starts with context and no
recap. Eight-category lint, autoresearch, six vault modes, a visual layer. If you want the
Karpathy pattern working this afternoon, this is how you get it.

What it leaves open is mostly about cost, and one thing about correctness:

| Open | Consequence |
|---|---|
| One conversational session mixes ingest and query | `effort` is part of the prompt-cache key. Switching mid-session re-reads the whole context at full price |
| `WIKI.md` + `CLAUDE.md` re-sent uncached each session | The most static text in the system, paid for every time |
| Flat index; sub-index only suggested for external projects | Inherits the ~100-source ceiling |
| No `aliases`, no duplicate-entity lint | Two pages for one entity, silently. The most common failure at scale |
| No validity interval on claims | `log.md` records *operations*, not whether a claim still holds |
| "Parallel agents" for batch ingest, run synchronously | Forfeits the 50% batch discount for no benefit — nobody waits on a backfill |

### Anthropic — [knowledge graph cookbook](https://platform.claude.com/cookbook/capabilities-knowledge-graph-guide)

**The pipeline, and an unusually honest evaluation.** Extract → resolve → assemble → query,
with each classical stage collapsed into a prompt: no trained NER, no relation classifier, no
brittle string heuristics. Entity resolution catches *"Edwin Aldrin" → "Buzz Aldrin"*, which
edit distance never will.

And then it publishes its own numbers, which is the part most write-ups omit:

| Document | Recall after resolution |
|---|---|
| Apollo 11 | **0.55** |
| Neil Armstrong | **0.38** |

Between 45% and 62% of entities lost. It also documents two failure modes: **silent loss**
(a name left out of every cluster vanishes with no warning) and **over-merge** ("Gemini 12"
absorbed into "Project Gemini").

Applied to a second brain, three further problems:

- A triple cannot hold *"the author argues X, but with reservation Y"*. Nuance is the thing
  a research vault is for.
- The result is unreadable by a human. You lose the artefact you were building.
- **It assumes the corpus is someone else's text.** This is the assumption that turns out
  to be false, and everything below follows from noticing it.

### rody — [Graph Engineering with Opus 5](https://x.com/0x_rody/status/2081664256571810178)

Not an architecture post; a **cost** post. Its architecture is the cookbook's. What it adds
is the operational layer, and three of its levers are worth taking:

- **Effort split** — extraction is mechanical, run it low; traversal is judgement, run it high
- **Stable prefix, variable last**, with `cache_control` on the schema
- **`effort` is part of the cache key** — flip it mid-session and the next turn re-reads
  everything at full price
- Batch API for backfills; `valid_from` for a temporal layer

Where it overreaches, and it is worth saying: the cost comparison is against a strawman
(*"no cache, high effort, synchronous"* is not what anyone does on purpose); the claim that
feeding a temporal graph is cheaper than embedding the same corpus is **false by one to two
orders of magnitude**; and it skips the most obvious lever entirely — it keeps everything on
the frontier model and saves with `effort` and caching, where the cookbook simply uses a
small model for extraction.

**The important realisation about this post: its levers are infrastructure, not graph
architecture.** They transfer to a plain wiki unchanged. The cost argument usually credited
to graphs is independent of graphs.

---

## The five gaps

Putting the four together, the same holes appear from both directions.

**1. Retrieval cost grows with the vault, not with the question.**
The wiki reads an index that catalogues everything. The graph reads a local neighbourhood.
Only one of those is flat as the corpus grows.

**2. Extraction throws away half of what it reads.**
0.38–0.55 recall, plus over-merge, plus silent loss. For a personal knowledge base built over
months, losing half of anything is not a tradeoff, it is a defect.

**3. Contradictions are found by brute force, or not at all.**
An O(n²) LLM pass is affordable at 30 pages and unaffordable at 300 — which is precisely when
contradictions start to matter. The check quietly stops being run.

**4. Claims rot silently.**
"Stale claim detection" as a lint heuristic means hoping the model notices that something
written eight months ago has been superseded. There is no structural reason it would.

**5. Nobody is watching the drift.**
Every page in a mature second brain was written by an LLM reading pages written by an LLM.
Errors are not corrected in transit — they are consolidated, and each rewrite makes them
sound more confident, because the prose improves even when the fact does not.

> A vault that has drifted and a vault that has compounded well **feel identical from the
> inside**. Both produce coherent, well-cross-referenced, confidently-cited answers.
> Internal coherence is not evidence of correctness.

This is the gap none of the four references addresses, and the one that gets worse with time
rather than better.

---

## What changes: declare, don't extract

Every graph pipeline assumes the corpus is **someone else's text** that you must extract from.
In a second brain that assumption is simply false. **You control the writing step.**

The model writing the page has the source open and the vault as context. It is the
best-placed observer in the system. Asking it to also emit its edges into frontmatter costs a
few dozen tokens on a write you were paying for anyway. An extractor reading that same page
three weeks later has strictly less information — which is exactly why it recovers 0.4 of the
entities.

From that one move, four of the five gaps close:

| Gap | How it closes |
|---|---|
| **2. Lost entities** | Recall ≈1.0 by construction. Over-merge cannot occur: the author knows which page they meant. Entity resolution becomes nearly unnecessary — the wikilink *is* the canonical identifier |
| **1. Retrieval cost** | With edges in frontmatter, the graph is derived by a script. Traversal (L0) costs zero tokens, frontmatter (L1) about 60/page, bodies (L2) only for the finalists |
| **3. Contradictions** | Declared at write time by the session best placed to notice. O(n²) LLM pass becomes an O(1) query |
| **4. Stale claims** | `valid_from` and `superseded_by` make expiry a query rather than a hope |

The fifth — drift — does not close by itself. It needs anchors: an immutable `.raw/` layer,
provenance that must terminate in a raw document rather than in another wiki page, and
`derivation_depth` as a measurable distance from ground truth. `wq.py unanchored` lists the
pages that fail that test.

**And the graph is not a second artefact.** It is a view, derived by script from the pages.
There is nothing to keep in sync, so nothing can diverge — which matters, because
double-maintenance is exactly the burden Karpathy identifies as what kills wikis.

---

## What you actually get

Concrete, measured on a real 28-node vault built while designing this.

| Operation | Plain LLM Wiki | LLM Wiki G² |
|---|---|---|
| "What connects to X?" | index + N pages | `jq` over `edges.json` — **0 tokens** |
| Normal query | whole index + 5–10 pages | L0 → L1 → L2 |
| "What contradicts what?" | O(n²) LLM pass | **O(1)** query |
| "What has gone stale?" | heuristic lint | query over `valid_from` |
| "What am I missing?" | intuition | `wq.py gaps` — declared holes |
| "What is not grounded?" | no answer available | `wq.py unanchored` |
| Query cost as vault grows | superlinear | ≈ flat |

**Measured:** frontmatter costs **23%** of what bodies cost. Filtering L0→L1 saved **89–94%**
against reading the same neighbourhood. Migrating the vault's own edges collapsed **46 ad-hoc
predicates into 14**, which is the difference between a graph you can query and a pile of
synonyms.

Three benefits that are harder to put in a table:

**You stop paying for growth.** The ~100-source ceiling is a token ceiling. Removing it is
what makes a multi-year vault viable rather than a thing you eventually abandon.

**Your maintenance becomes checkable.** `wq.py lint` finds broken links, orphans, pages with
no relations, expired claims and unanchored provenance for free. Only what it flags deserves
an LLM pass. Before, "is my wiki healthy?" had no cheap answer, so it went unasked.

**You can tell whether it is working.** The vault is a git repo, and `snapshot.sh` mounts a
past state in a worktree. Answer the same questions against today's vault and last month's,
same model, same settings. Without holding the model and the operator constant, you are
measuring your own improvement at asking questions — which feels exactly the same from the
inside.

---

## What it costs

Honest ledger.

- **Discipline at write time.** Every page needs 5–7 declared edges from a closed vocabulary.
  A lazy session creates a node invisible to the graph. The lint flags it, but the lint is
  not the author.
- **A vocabulary that may not fit you.** Fourteen predicates, closed by design. If your domain
  needs different ones, change them — but deliberately and in a versioned commit, not ad hoc,
  or you are back to 46 synonyms.
- **Serendipity, partially.** Declared edges are the ones the writing session noticed. A
  neutral reader might find connections the author missed. `wq.py undeclared` recovers some of
  it by comparing prose links to declared edges, at zero cost, but not all.
- **A migration.** For an existing vault: a script pass, then a batched LLM pass to type the
  candidate edges. The script pass is free and reversible; the typing is real work.

---

## Who should not use this

- **Vaults under ~50 pages.** Below that, the retrieval protocol costs more than reading
  everything — `wq.py context` will tell you so in plain language rather than reporting a
  negative saving. Just read the pages.
- **Anyone who wants zero write-time overhead.** Declaration is the whole trade. If you will
  not declare edges, you get a plain LLM Wiki with extra frontmatter.
- **Anyone who needs a finished product.** This is a design hypothesis with a working
  implementation, not a validated result.

---

## What is not proven

Worth stating plainly, because the rest of this document argues confidently.

The design has been **tested for correctness** — 33 checks across two suites, on macOS and
Linux, Python 3.9 and 3.11 — but its central claims have not been **validated at scale**.
Everything measured above comes from a 28-node vault. The behaviour that matters happens at
300 and at 3,000.

[`docs/design.md`](design.md) closes with three falsifiable predictions, including the one
that would sink the whole thing: *on a fixed gold set, answers via L0→L1→L2 should match or
beat index→pages with fewer tokens. If they are worse, prose matters more than this design
assumes.*

If you run that comparison on a real vault, the result is worth an issue either way. A
negative result is more useful than another opinion.
