#!/bin/bash
# Deploy a commit that is already pushed to the development branch.
# Usage: scripts/ops/deploy.sh SHA [FILE ...]
#   1. waits until the push CI runs for SHA have finished (polls the GitHub API once a minute;
#      the unauthenticated limit is 60 requests per hour);
#   2. refuses unless every run succeeded and main can be fast-forwarded to SHA;
#   3. pushes SHA to main (GitHub Pages then rebuilds);
#   4. waits until the live site serves the committed VERSION and every listed FILE byte for byte.
# Environment: RUNS_API (GitHub Actions runs endpoint), SITE (public base URL).
set -u
SHA=${1:?usage: deploy.sh SHA [FILE ...]}; shift
RUNS_API=${RUNS_API:-https://api.github.com/repos/EugeneYip/civiclens/actions/runs}
SITE=${SITE:-https://civiclens.eugeneyip.net}
cd "$(git rev-parse --show-toplevel)" || exit 1
FULL=$(git rev-parse "$SHA") || exit 1
L=""
for i in $(seq 1 40); do
  L=$(curl -s "$RUNS_API?head_sha=$FULL&event=push" | python3 -c "import json,sys
try: r=json.load(sys.stdin)['workflow_runs']
except Exception: print('0 api_unreadable'); sys.exit()
print(len(r),' '.join(x['name'].replace(' ','_')+':'+x['status']+':'+str(x['conclusion']) for x in r))")
  N=${L%% *}
  if [ "$N" -ge 2 ] && ! echo "$L" | grep -q -e ':queued' -e ':in_progress' -e ':waiting'; then break; fi
  sleep 60
done
echo "CI: $L"
[ "${L%% *}" -ge 2 ] 2>/dev/null || { echo CI_UNKNOWN; exit 1; }
echo "$L" | grep -q -e ':failure' -e ':cancelled' -e ':None' && { echo CI_FAILED; exit 1; }
git fetch -q origin main && git merge-base --is-ancestor origin/main "$FULL" || { echo NOT_FF; exit 1; }
git push origin "$FULL:main" 2>&1 | tail -1
want=$(git show "$FULL:VERSION" | tr -d '\n')
for i in $(seq 1 80); do
  got=$(curl -s "$SITE/VERSION?nc=$RANDOM$RANDOM" | tr -d '\n'); [ "$got" = "$want" ] && break; sleep 15
done
echo "live VERSION=$got (want $want)"
for f in "$@"; do  # poll, because Pages may lag even when VERSION is unchanged (data-only commits)
  a=$(git show "$FULL:$f" | sha256sum | cut -c1-16)
  for i in $(seq 1 40); do b=$(curl -s "$SITE/$f?nc=$RANDOM$RANDOM" | sha256sum | cut -c1-16); [ "$a" = "$b" ] && break; sleep 15; done
  echo "$f local=$a live=$b $([ "$a" = "$b" ] && echo OK || echo MISMATCH)"
done
