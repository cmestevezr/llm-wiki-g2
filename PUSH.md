# How to publish this

The repo is committed locally and every URL already points at
`github.com/cmestevezr/llm-wiki-g2`. Nothing to find-and-replace.

## 1. Create the empty repo

On github.com → New repository → owner `cmestevezr`, name `llm-wiki-g2` →
**do not** tick README, .gitignore or licence. They already exist here, and adding
them creates a conflicting initial commit you would have to merge.

## 2. Push

```bash
cd "/Volumes/K2T/Documentos K2T/llm-wiki-g2"
git remote add origin https://github.com/cmestevezr/llm-wiki-g2.git
git branch -M main
git push -u origin main
```

If you use SSH instead:

```bash
git remote add origin git@github.com:cmestevezr/llm-wiki-g2.git
```

## 3. Sanity check before announcing

```bash
bash tests/test-migration.sh          # should print 8 passed, 0 failed
grep -rn 'llm-wiki-g2' README.md docs/ .claude-plugin/ templates/ | grep -v cmestevezr
```

The second command should return nothing. If it prints a line, a URL was missed.

The tests matter more than usual here: the five migration guarantees *are* the pitch.
If someone's first experience is losing a note, no README saves it.

## 4. Repo settings worth doing

- **Description:** "Turn an LLM Wiki into a derived knowledge graph. Edges declared at
  write time, not extracted at read time."
- **Topics:** `obsidian` `llm-wiki` `knowledge-graph` `second-brain` `pkm`
  `claude-code` `graph-engineering`
- Enable Issues. `docs/design.md` ends with three falsifiable predictions — that is an
  invitation for people to report results back, and results are what would make this
  more than an opinion.

## 5. Optional — the author name

`.claude-plugin/plugin.json` lists the author as **Karelman**, which is how you
identified yourself, not your GitHub handle. That mismatch is normal and harmless.
Change it if you would rather they match:

```bash
sed -i '' 's/"name": "Karelman"/"name": "cmestevezr"/' .claude-plugin/plugin.json
```

## 6. Then remove this file

```bash
git rm PUSH.md && git commit -m "Remove publishing notes"
```
