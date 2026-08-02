---
name: g2-setup
description: Set up or upgrade a vault to LLM Wiki G². Detects whether the folder is empty, already an LLM Wiki, or already G², and takes the right path. Triggers on "set up g2", "/g2", "upgrade my wiki", "install llm wiki g2", "turn this into a knowledge graph", "scaffold a wiki".
---

# g2-setup — detect, then act

You are setting up **LLM Wiki G²** in the user's vault. Your first job is to find out what
you are looking at. Do not scaffold blindly and do not migrate blindly.

## Step 1 — detect

Run these and read the answers before doing anything:

```bash
ls -a "$VAULT"
find "$VAULT" -name '*.md' -not -path '*/.*' | head -50
find "$VAULT" -name '*.md' -not -path '*/.*' | wc -l
ls "$VAULT/.git" 2>/dev/null && echo "git: yes" || echo "git: no"
test -f "$VAULT/CLAUDE.md" && echo "has CLAUDE.md"
test -f "$VAULT/AGENTS.md" && echo "has AGENTS.md"
grep -rl 'derivation_depth' "$VAULT" 2>/dev/null | head -1
```

Classify into exactly one:

| State | Signal | Path |
|---|---|---|
| **A. Empty** | no `.md` files, or only untouched Obsidian config | Step 2 — scaffold |
| **B. Existing LLM Wiki** | `.md` files present, no `derivation_depth` anywhere | Step 3 — migrate |
| **C. Already G²** | `derivation_depth` appears in frontmatter | Step 4 — verify only |

If it is ambiguous — say, three stray notes — **ask the user** which they meant. Do not guess.

## Step 2 — scaffold (empty vault)

1. Create the folder structure:
   `wiki/{sources,concepts,entities,questions,gaps,meta}` and `.raw/` and `bin/`.
2. Copy `templates/vault-CLAUDE.md` to the vault root as `CLAUDE.md`.
3. Copy `bin/build-edges.py`, `bin/wq.py`, `bin/snapshot.sh` into the vault's `bin/`.
4. Copy `templates/obsidian/*` into `.obsidian/` — **merge, never overwrite**: if
   `graph.json` already exists, add the `colorGroups` key and leave every other key alone.
5. Create `wiki/index.md`, `wiki/log.md`, `wiki/hot.md`, `wiki/overview.md` from
   `templates/wiki/`.
6. `git init` and commit, unless the user declines.
7. Ask the user **one** question: *what is this vault for?* Use their answer to write
   `wiki/overview.md` and to tailor the folder set — a book-reading vault wants
   `wiki/characters/`, a research vault does not.
8. Tell them the next step is to drop a source into `.raw/` and say "ingest it".

## Step 3 — migrate (existing LLM Wiki)

**Read `skills/g2-migrate/SKILL.md` and follow it.** Do not improvise a migration.
The short version: `migrate.py` in dry run, show the user the report, get consent,
apply with `--backup`, verify, then type the candidate edges in batches.

The one thing you must never do here: rewrite, reword, reformat or reorganise their
existing prose. Not one line. Their pages are theirs.

## Step 4 — already G²

Run the health check and report. Do not re-scaffold.

```bash
python3 bin/build-edges.py --vault "$VAULT"
python3 bin/wq.py --vault "$VAULT" lint
python3 bin/wq.py --vault "$VAULT" stats
```

## Guardrails

- **Never overwrite an existing `CLAUDE.md` or `AGENTS.md`.** If one exists, show the user
  what G² would add and offer to append a clearly-marked section instead.
- **Never delete anything.** Not a file, not a frontmatter key, not a line of prose.
- **Never move files** without explicit consent, and even then commit first.
- If `git` is absent, offer to initialise it and explain why: it is the restore point and
  the evaluation time machine. Accept "no" gracefully and continue with `--no-git`.
- Prefer running the scripts over doing the work yourself in context. `build-edges.py`
  costs zero tokens; you reading every page does not.
