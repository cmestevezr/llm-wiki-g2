# How to publish this

The repo is committed locally. To put it on GitHub:

## 1. Create the empty repo

On github.com → New repository → name it `llm-wiki-g2` → **do not** add a README,
.gitignore or licence (they already exist here).

## 2. Push

```bash
cd "/Volumes/K2T/Documentos K2T/llm-wiki-g2"
git remote add origin https://github.com/YOUR-USERNAME/llm-wiki-g2.git
git branch -M main
git push -u origin main
```

## 3. Fix the placeholder URLs

Three files say `karelman/llm-wiki-g2`. If your GitHub username differs:

```bash
grep -rn 'karelman/llm-wiki-g2' README.md docs/ .claude-plugin/ templates/
```

## 4. Repo settings worth doing

- **Description:** "Turn an LLM Wiki into a derived knowledge graph. Edges declared at
  write time, not extracted at read time."
- **Topics:** `obsidian` `llm-wiki` `knowledge-graph` `second-brain` `pkm`
  `claude-code` `graph-engineering`
- Enable Issues. The three falsifiable predictions in `docs/design.md` are an invitation
  for people to report results.

## 5. Before announcing

Run the tests once on your own machine — the guarantees are the whole pitch:

```bash
bash tests/test-migration.sh
```

Then delete this file:

```bash
git rm PUSH.md && git commit -m "Remove publishing notes"
```
