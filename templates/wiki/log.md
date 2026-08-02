---
type: log
title: "Log"
created: {{DATE}}
updated: {{DATE}}
---

# Log

Append-only. **New entries at the top.**

Consistent prefixes make this greppable:
`grep "^## \[" wiki/log.md | head -5`

## [{{DATE}}] scaffold | Vault initialised
- Structure created, `CLAUDE.md` schema in place
- `bin/` scripts installed
