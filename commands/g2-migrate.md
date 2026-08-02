---
description: Upgrade an existing LLM Wiki to G² - dry run, report, consent, apply, verify.
---

Follow the `g2-migrate` skill exactly. Do not improvise.

Start with the dry run and show the user the report before anything else:

```bash
python3 bin/migrate.py --vault . 
```

Then walk them through `.g2/migration-report.md`, get explicit consent, and only then apply
with `--backup`. Verify afterwards and tell them how to revert.

Their prose is immutable. You are adding frontmatter and nothing else.

$ARGUMENTS
