#!/usr/bin/env bash
#
# Load + error simulator for the alert -> trace -> log correlation lab.
# Exercises every endpoint exposed by web/routes.py.
#
# Usage:
#   HOST=http://ec2-1-2-3-4.eu-west-1.compute.amazonaws.com ./load-test.sh
#
# Env vars (all optional):
#   HOST              base URL of the deployed app (default: localhost)
#   DURATION_SECONDS  how long to run     (default: 660 — must exceed 10m for `for: 10m` alerts)
#   WORKERS           parallel clients    (default: 5)
#   RPS               requests/sec/worker (default: 10)
#   ERROR_RATIO       % of requests that intentionally error (default: 25 — must exceed 5% threshold)
#
set -u

HOST="${HOST:-http://ec2-18-201-244-108.eu-west-1.compute.amazonaws.com}"
DURATION_SECONDS="${DURATION_SECONDS:-660}"
WORKERS="${WORKERS:-5}"
RPS="${RPS:-10}"
ERROR_RATIO="${ERROR_RATIO:-25}"

INTERVAL=$(awk "BEGIN { printf \"%.3f\", 1/$RPS }")

log() { printf "[%s] %s\n" "$(date +%H:%M:%S)" "$*"; }

# -------------------------------------------------------------------
# Happy-path requests — exercise all CRUD endpoints
# (skips /api/health and /metrics: trivial work, not lab-relevant)
# -------------------------------------------------------------------
hit_list() { curl -s -o /dev/null "${HOST}/api/topics"; }

# Full CRUD lifecycle: POST -> GET -> PUT -> DELETE
crud_flow() {
    local body="{\"title\":\"crud-$RANDOM-$(date +%s%N)\",\"description\":\"perf test\"}"
    local resp id
    resp=$(curl -s -X POST -H "Content-Type: application/json" \
        -d "$body" "${HOST}/api/topics")
    id=$(printf '%s' "$resp" | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)
    [ -z "$id" ] && return

    curl -s -o /dev/null "${HOST}/api/topics/$id"
    curl -s -o /dev/null -X PUT -H "Content-Type: application/json" \
        -d "{\"title\":\"updated-$RANDOM\"}" "${HOST}/api/topics/$id"
    curl -s -o /dev/null -X DELETE "${HOST}/api/topics/$id"
}

# -------------------------------------------------------------------
# Error-generating requests — drive http_errors_total + trace exemplars
# -------------------------------------------------------------------
err_post_empty()  { curl -s -o /dev/null -X POST -H "Content-Type: application/json" -d '{}' "${HOST}/api/topics"; }
err_put_empty()   { curl -s -o /dev/null -X PUT  -H "Content-Type: application/json" -d '{}' "${HOST}/api/topics/1"; }
err_get_missing() { curl -s -o /dev/null "${HOST}/api/topics/9999999"; }
err_put_missing() { curl -s -o /dev/null -X PUT -H "Content-Type: application/json" -d '{"title":"x"}' "${HOST}/api/topics/9999999"; }
err_del_missing() { curl -s -o /dev/null -X DELETE "${HOST}/api/topics/9999999"; }

# -------------------------------------------------------------------
# Worker
# -------------------------------------------------------------------
worker() {
    local id=$1
    local end=$(( $(date +%s) + DURATION_SECONDS ))
    local count=0 errs=0

    while [ "$(date +%s)" -lt "$end" ]; do
        local roll=$((RANDOM % 100))
        if [ "$roll" -lt "$ERROR_RATIO" ]; then
            case $((RANDOM % 5)) in
                0) err_post_empty ;;
                1) err_put_empty ;;
                2) err_get_missing ;;
                3) err_put_missing ;;
                4) err_del_missing ;;
            esac
            errs=$((errs + 1))
        else
            case $((RANDOM % 2)) in
                0) hit_list ;;
                1) crud_flow ;;
            esac
        fi
        count=$((count + 1))
        sleep "$INTERVAL"
    done
    log "worker $id done: $count requests ($errs errors)"
}

# -------------------------------------------------------------------
# Run
# -------------------------------------------------------------------
log "Target:      $HOST"
log "Duration:    ${DURATION_SECONDS}s"
log "Workers:     $WORKERS  (~$((WORKERS * RPS)) rps total)"
log "Error ratio: ${ERROR_RATIO}%"
log "Endpoints exercised:"
log "   GET    /api/topics"
log "   POST   /api/topics       (valid + empty-body 400)"
log "   GET    /api/topics/:id   (valid + 404)"
log "   PUT    /api/topics/:id   (valid + empty-body 400 + 404)"
log "   DELETE /api/topics/:id   (valid + 404)"
log "----------------------------------------"

for i in $(seq 1 "$WORKERS"); do
    worker "$i" &
done
wait

log "----------------------------------------"
log "Load test complete. Verify the correlation chain:"
log ""
log "  1. PROMETHEUS  ${HOST}:9090/alerts"
log "     -> HighErrorRate FIRING (>5% errors for 10m)"
log ""
log "  2. GRAFANA     ${HOST}/monitoring/"
log "     -> 'Aggregate Error Rate %' panel above 5% red threshold"
log "     -> 'Recent Error Traces' table populated with traceIDs"
log "     -> Click 'View Trace in Jaeger' on any row"
log ""
log "  3. JAEGER      ${HOST}/jaeger/"
log "     -> Failed span shown with error=true tag"
log "     -> Copy the trace_id from the URL"
log ""
log "  4. CLOUDWATCH  log group /docker/web-app"
log "     -> Filter:  { \$.trace_id = \"<paste trace_id>\" }"
log "     -> See the full structured log line for that exact request"
