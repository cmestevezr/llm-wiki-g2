# bin/ — derived views

Deterministic scripts. They **read `wiki/`, never write to it.** No LLM, no tokens.

```bash
pip install pyyaml          # the only dependency
```

| Script | What it does |
|---|---|
| `build-edges.py` | Derives `edges.json` from frontmatter. Run after any write |
| `wq.py` | L0/L1 queries over `edges.json` |
| `migrate.py` | Upgrades an existing LLM Wiki, additively and reversibly |
| `snapshot.sh` | Mounts a past state of the vault for controlled comparison |

## wq.py

| Command | For |
|---|---|
| `neighbors <page> --depth N` | topological neighbourhood (L0) |
| `context <page> --budget N` | frontmatter of the neighbourhood (L1) |
| `path <A> <B>` | shortest path |
| `contradictions` | declared contradictions — O(1) |
| `stale --days N` | claims past their review horizon |
| `hubs --top N` | in-degree concentration |
| `undeclared` | prose links with no edge: candidates |
| `unanchored` | claims with no chain to a raw source |
| `gaps` | open frontier |
| `lint` | every defect |
| `stats` | graph summary |

All commands take `--vault PATH` (defaults to the repo root).

## migrate.py

Five guarantees, all tested in `tests/test-migration.sh`:

1. **Dry run by default** — nothing written without `--apply`
2. **Body invariant** — every page body stays byte-identical, verified after writing;
   the run aborts and restores if it isn't
3. **Additive only** — existing frontmatter keys are never modified or removed
4. **Idempotent** — a second run changes nothing
5. **Git guarded** — refuses to apply on a dirty tree

```bash
python3 bin/migrate.py --vault ~/my-wiki                    # dry run + report
python3 bin/migrate.py --vault ~/my-wiki --apply --backup
python3 bin/migrate.py --vault ~/my-wiki --verify
```

It deliberately does **not** guess predicates. A script cannot tell `contradicts` from
`qualifies`. It reports candidate edges and leaves the typing to phase 2.

## snapshot.sh

```bash
bin/snapshot.sh --list
bin/snapshot.sh "1 month ago"
bin/snapshot.sh --clean
```

Uses a `git worktree`, so it never touches the current vault.

## Note on external drives

On exFAT/NTFS volumes git can leave a stale `.git/index.lock` when the filesystem denies
`unlink`. If a commit fails with *"Another git process seems to be running"* and none is:

```bash
rm -f .git/index.lock .git/HEAD.lock
```
