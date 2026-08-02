---
description: Health-check the vault. Script first, LLM only on what it flags.
---

Follow the `g2-lint` skill. Run the free checks first:

```bash
python3 bin/build-edges.py --vault .
python3 bin/wq.py --vault . lint
python3 bin/wq.py --vault . stale --days 90
python3 bin/wq.py --vault . unanchored
python3 bin/wq.py --vault . undeclared --min-count 2
```

Then reason only over what those surfaced. Report findings; ask before editing.

$ARGUMENTS
