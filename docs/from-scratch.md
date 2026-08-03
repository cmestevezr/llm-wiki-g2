# Starting from scratch

## What you need first — probably less than you think

**You do not need Obsidian, and you do not need to create a vault beforehand.**

An "Obsidian vault" is not a format. It is a folder containing markdown files. Obsidian
creates its `.obsidian/` config directory the first time you open the folder, and that
directory is the only thing that makes it look special. Nothing in this project reads it.

So the whole prerequisite is:

```bash
mkdir my-wiki && cd my-wiki
```

You need Python 3.8+, PyYAML and git. That is the list.

Obsidian is a **viewer**, and a good one — graph view, backlinks, colour coding. Install it
whenever you feel like seeing your vault instead of querying it, point it at the same folder
with *Open folder as vault*, and enable the CSS snippet. Or don't. The scripts and the
retrieval protocol behave identically either way.

## Install

```bash
claude plugin marketplace add cmestevezr/llm-wiki-g2
claude plugin install llm-wiki-g2@llm-wiki-g2-marketplace
```

Or clone and copy `bin/`, `templates/vault-CLAUDE.md` and `templates/obsidian/` into your
vault by hand. Nothing here needs the plugin system to work.

## Scaffold

Open Claude in that folder and type `/g2`. You get:

```
.raw/                 your sources — immutable, the agent never writes here
wiki/
  sources/            one page per ingested source        green
  concepts/           ideas, patterns, techniques         blue
  entities/           people, orgs, tools                 purple
  questions/          syntheses, comparisons              amber
  gaps/               what the vault does NOT know        red
  meta/               decisions and session records       grey
  index.md log.md hot.md overview.md
bin/                  the scripts
CLAUDE.md             the schema
```

It will ask you **one** question: what is this vault for. The answer shapes `overview.md`
and the folder set — a vault for reading a novel wants `wiki/characters/`; a research vault
does not.

## The loop

**Ingest.** Drop something into `.raw/` and say "ingest it". Claude reads it, writes a source
page at `derivation_depth: 0`, updates the concepts and entities it touches, and **declares
the edges while writing**. Then it rebuilds the graph and commits.

**Query.** Ask a question. Claude goes `hot.md` → L0 topology → L1 frontmatter → L2 bodies,
and cites specific pages. Retrieval cost stays roughly flat as the vault grows, which is the
whole point.

**Lint.** Say "lint the wiki". The script finds broken links, orphans, pages with no
relations, expired claims and unanchored provenance for free; only what it flags gets an LLM
pass.

**Save.** When an answer took real work, file it back into `wiki/questions/`. This is what
makes your explorations compound the same way ingested sources do.

## Two habits that decide whether this works

**Separate your sessions.** Ingest in one, query in another. `effort` is part of the
prompt-cache key: a session that ingests at low effort and then queries at high effort
re-reads its entire context at full price at the moment it switches.

**Declare contradictions the moment you notice one.** It is the highest-value thing you do
all session. An undeclared contradiction becomes a silently wrong answer later, and the
O(n²) lint pass that would have caught it is exactly the pass nobody runs once the vault is
big.

## First week

Ingest five to ten real sources before judging anything. Below that the graph is too sparse
for the retrieval protocol to beat just reading everything, and you will conclude the design
does nothing.

Once you are past twenty pages:

```bash
python3 bin/wq.py hubs
python3 bin/wq.py stats
```

If the top ten nodes hold most of the edges, your vault is hub-shaped — and the useful work
is consolidating those hubs, not adding nodes. Node count is easy to measure and usefulness
is not, which is exactly why people optimise the wrong one.

## Set up the comparison early

```bash
git add -A && git commit -m "week 1"
```

In a month you will want to know whether the vault actually got better or whether you just
got better at asking it questions. `bin/snapshot.sh "1 month ago"` lets you answer the same
questions against both states with the same model and settings. That comparison only exists
if you were committing from the start.
