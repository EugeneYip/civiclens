#!/bin/bash
# One election-night refresh: fetch official CEC counts -> validate -> test -> commit -> push ->
# wait for CI -> fast-forward main -> confirm the live data. Prints one status line:
# LIVE / NOCHANGE / ADAPTER_FAIL / BUILD_FAIL / REF_FAIL / MAP_FAIL / TEST_FAIL / CI_FAIL / NOT_FF.
# Nothing is published unless every step passes; on failure the data files are restored.
# Usage (loop example): for n in $(seq 1 12); do sleep 540; scripts/ops/refresh_results.sh; done
# Environment: WORK (scratch directory for downloaded pages; untrusted data), BRANCH, RUNS_API, SITE,
#   COMMIT_TRAILER (optional extra commit-message paragraph, e.g. co-author lines).
set -u
cd "$(git rev-parse --show-toplevel)" || exit 1
WORK=${WORK:-${TMPDIR:-/tmp}/civiclens-results}; BRANCH=${BRANCH:-$(git branch --show-current)}
RUNS_API=${RUNS_API:-https://api.github.com/repos/EugeneYip/civiclens/actions/runs}
SITE=${SITE:-https://civiclens.eugeneyip.net}
FILES="data/results-snapshot.json data/referendum-result.json data/results-map.json"
R=$WORK/r_$(date -u +%H%M); rm -rf "$R"; mkdir -p "$WORK"
python3 -I scripts/adapt_cec_vote.py "$R" > "$R.log" 2>&1 || { echo "ADAPTER_FAIL $(tail -3 "$R.log" | tr '\n' ' ')"; exit 1; }
python3 scripts/build_results_snapshot.py "$R"/*.json > "$R.build" 2>&1 || { echo "BUILD_FAIL $(tail -2 "$R.build" | tr '\n' ' ')"; git checkout -q $FILES; exit 1; }
python3 -I scripts/build_referendum_result.py "$R/ref" > "$R.ref" 2>&1 || { echo "REF_FAIL $(tail -1 "$R.ref")"; git checkout -q data/referendum-result.json; }
python3 scripts/build_results_map.py > "$R.map" 2>&1 || { echo "MAP_FAIL $(tail -1 "$R.map")"; git checkout -q $FILES; exit 1; }
if git diff --quiet $FILES; then echo "NOCHANGE $(head -1 "$R.log")"; exit 0; fi
python3 -m pytest -q tests/test_results_snapshot.py tests/test_image_audit.py tests/test_referendum.py tests/test_results_map.py > "$R.test" 2>&1 || { echo "TEST_FAIL"; git checkout -q $FILES; exit 1; }
SUM=$(python3 -c "
import json;r=json.load(open('data/results-snapshot.json'))['races'];f=sum(x['status']=='final' for x in r.values())
st=[x['stations'] for k,x in r.items() if k.endswith('-chief') and 'stations' in x];rep=sum(s['reported'] for s in st);tot=sum(s['total'] for s in st)
print(f'{f}/{len(r)} races final, stations {rep}/{tot}, CEC {max(x[\"published_at\"] for x in r.values())[11:16]}')")
git add $FILES
git commit -q -m "Update official CEC vote counts: $SUM" ${COMMIT_TRAILER:+-m "$COMMIT_TRAILER"}
SHA=$(git rev-parse HEAD)
for i in 1 2 3 4; do git push -q -u origin "$BRANCH" 2>/dev/null && break; sleep $((i*3)); done
for i in $(seq 1 30); do
  L=$(curl -s "$RUNS_API?head_sha=$SHA&event=push" | python3 -c "import json,sys
try: r=json.load(sys.stdin)['workflow_runs']
except Exception: print('0'); sys.exit()
print(len(r),' '.join(x['status']+':'+str(x['conclusion']) for x in r))")
  N=${L%% *}; if [ "$N" -ge 2 ] && ! echo "$L" | grep -q -e queued -e in_progress -e waiting; then break; fi; sleep 45
done
echo "$L" | grep -q -e failure -e cancelled -e ':None' && { echo "CI_FAIL ${SHA:0:7} $L"; exit 1; }
[ "${L%% *}" -ge 2 ] 2>/dev/null || { echo "CI_UNKNOWN ${SHA:0:7}"; exit 1; }
git fetch -q origin main && git merge-base --is-ancestor origin/main HEAD || { echo "NOT_FF ${SHA:0:7}"; exit 1; }
git push -q origin HEAD:main
want=$(git show HEAD:data/results-snapshot.json | sha256sum | cut -c1-16)
for i in $(seq 1 40); do got=$(curl -s "$SITE/data/results-snapshot.json?nc=$RANDOM$RANDOM" | sha256sum | cut -c1-16); [ "$got" = "$want" ] && break; sleep 15; done
[ "$got" = "$want" ] && echo "LIVE ${SHA:0:7} $SUM" || echo "LIVE_PENDING ${SHA:0:7} $SUM"
