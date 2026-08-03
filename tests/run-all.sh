#!/usr/bin/env bash
# Runs every suite. Exits non-zero if any fails.
set -uo pipefail
D="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RC=0
for t in "$D"/test-*.sh; do
  bash "$t" || RC=1
  echo
done
[ $RC -eq 0 ] && echo "ALL SUITES PASSED" || echo "SOME SUITES FAILED"
exit $RC
