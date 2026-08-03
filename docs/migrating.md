# Migrating an existing LLM Wiki

You have months of notes. The migration treats them as immutable: it adds frontmatter and
nothing else. Your prose comes out byte-identical, and there is a test that proves it.

## What actually changes

Only these keys, and only where they are absent:

| Field | Why it earns its place |
|---|---|
| `type` | routes the page into the graph |
| `valid_from` | turns stale-claim detection from a lint pass into a query |
| `superseded_by` | lets a claim expire instead of rotting silently |
| `derivation_depth` | LLM hops from an immutable source — the anti-drift instrument |
| `relations` | the declared edges. Seeded empty, for phase 2 |
| `sources` | provenance chain |
| `aliases` | entity resolution, for free |

`title` is added only on pages that had no frontmatter at all.

Nothing else is touched. No key is modified, no key is removed, no file is moved or renamed,
and not one line of prose changes.

## Where the scripts live

`migrate.py` runs **from a clone of this repo**, pointing at your vault. It is not installed
into your vault and does not need to be:

```bash
git clone https://github.com/cmestevezr/llm-wiki-g2
cd llm-wiki-g2
```

Every command below is run from that directory. If you installed the plugin instead, tell
Claude "upgrade my wiki" and it resolves the paths itself.

After the migration you will want `build-edges.py`, `wq.py` and `snapshot.sh` **inside** your
vault, since you will run them daily:

```bash
mkdir -p ~/my-wiki/bin
cp bin/build-edges.py bin/wq.py bin/snapshot.sh ~/my-wiki/bin/
```

## Phase 1 — scaffolding (a script, zero risk)

```bash
python3 bin/migrate.py --vault ~/my-wiki
```

Dry run. It writes `.g2/migration-report.md` and nothing else. Read it — it tells you how
many pages are affected, what type it inferred for each folder, which pages it will skip,
and what edges it found in your prose.

Types are inferred from folder names (`summaries/` → `source`, `topics/` → `concept`, and so
on). Wrong guesses are cheap: edit `type:` on the page and rebuild.

When you're satisfied:

```bash
git -C ~/my-wiki add -A && git -C ~/my-wiki commit -m "Before LLM Wiki G2"
python3 bin/migrate.py --vault ~/my-wiki --apply --backup
python3 bin/migrate.py --vault ~/my-wiki --verify
```

`--verify` reads the git diff and confirms every changed line is one of the keys above.

Cold feet at any point:

```bash
git -C ~/my-wiki checkout -- .
```

### Pages with broken frontmatter

Skipped, listed in the report, left exactly as they were. The script will not attempt to fix
YAML it cannot parse — guessing at malformed frontmatter is how you lose data. Fix them by
hand and re-run; the migration is idempotent, so re-running is free.

## Phase 2 — typing the edges (an LLM, batched)

After phase 1 every page has `relations: []`. The graph does not exist yet.

The script does not guess predicates on purpose. Telling `contradicts` from `qualifies` is a
semantic judgement, and a wrong edge is worse than a missing one — the missing one shows up
in `wq.py undeclared`, the wrong one is invisible forever.

```bash
python3 bin/wq.py --vault ~/my-wiki undeclared --min-count 1
```

Every link already in your prose that has no declared relation. These are your candidates,
found for free.

Ask Claude to type them **in batches of 20–30**, using only the 14 predicates in your
`CLAUDE.md`. Review each batch before it is written. Then:

```bash
python3 bin/build-edges.py --vault ~/my-wiki
git -C ~/my-wiki add -A && git -C ~/my-wiki commit -m "g2: edges, batch 1"
```

### Do this phase cheaply

It is high-volume mechanical work, and the levers are large:

- **Cheap model, low effort.** Pattern matching, not reasoning.
- **Cache the prefix.** Keep the schema and instructions identical on every call and put the
  variable page text last. A prefix that changes does not cache.
- **Batch API** for a large vault. Nobody is waiting on a backfill.
- **Do not flip effort mid-session** — it is part of the cache key, and flipping it re-reads
  your whole context at full price.

For a 300-page vault this is the difference between an afternoon of frontier-model calls and
a few dollars overnight.

## Phase 3 — anchoring (ongoing, optional)

```bash
python3 bin/wq.py --vault ~/my-wiki unanchored
```

Pages whose provenance ends at another wiki page rather than at a raw source. Fill in
`sources:` and `derivation_depth:` as you revisit them. Do not block the migration on this —
it is maintenance, and it never finishes.

## Afterwards

Retrieval changes. Instead of reading `index.md` and opening ten pages:

```bash
python3 bin/wq.py --vault ~/my-wiki context "Some Page" --depth 2
```

Add `edges.json` to your `.gitignore` — it is derived and regenerates in a second.

## If your vault is not in git

The script will refuse to apply and show you the three commands to fix it. You can override
with `--no-git`, but you lose the restore point *and* the snapshot comparison, which is the
only rigorous way to tell whether your wiki is getting better or you are just getting better
at asking it questions.

## Known friction

On exFAT/NTFS external drives, git can leave a stale `.git/index.lock` because the
filesystem denies `unlink`. If a commit fails with *"Another git process seems to be
running"* and none is:

```bash
rm -f .git/index.lock .git/HEAD.lock
```
