#!/usr/bin/env bash
set -euo pipefail
# This script creates/removes disposable containers. Never run it on production.
[[ "${CI:-}" == "true" && "${GITHUB_ACTIONS:-}" == "true" ]] || { echo 'Run only in GitHub Actions.'; exit 2; }
: "${TEST_IMAGE:?Missing TEST_IMAGE}"
prefix="cf-ci-${GITHUB_RUN_ID:-test}-${RANDOM}"
db="${prefix}-db"; redis="${prefix}-redis"; app="${prefix}-app"
cleanup() {
  status=$?
  if [[ "$status" != 0 ]]; then
    python3 scripts/container_lifecycle.py diagnose "$app" "$db" "$redis" || true
  fi
  docker rm -f "$app" "$db" "$redis" >/dev/null 2>&1 || true
  docker network rm "$prefix" >/dev/null 2>&1 || true
  exit "$status"
}
trap cleanup EXIT
docker network create "$prefix" >/dev/null
docker run -d --name "$db" --network "$prefix" --network-alias db --memory 512m \
  -e POSTGRES_USER=cf_ci -e POSTGRES_PASSWORD=cf_ci_disposable_only -e POSTGRES_DB=centralflow_ci \
  postgres:16-alpine >/dev/null
docker run -d --name "$redis" --network "$prefix" --network-alias redis --memory 128m redis:7-alpine >/dev/null
ready=false
for i in $(seq 1 60); do
  if docker exec "$db" pg_isready -U cf_ci -d centralflow_ci >/dev/null 2>&1; then ready=true; break; fi
  sleep 2
done
[[ "$ready" == true ]] || { echo 'Disposable PostgreSQL did not start.'; exit 1; }
docker run -d --name "$app" --network "$prefix" --memory 1536m -p 127.0.0.1::8080 \
  -e SERVER_PORT=8080 -e GLOBAL_API_KEY=ci_key_not_for_production \
  -e 'POSTGRES_AUTH_DB=postgresql://cf_ci:cf_ci_disposable_only@db:5432/centralflow_auth?sslmode=disable' \
  -e 'POSTGRES_USERS_DB=postgresql://cf_ci:cf_ci_disposable_only@db:5432/centralflow_ci?sslmode=disable' \
  -e CLIENT_NAME=centralflow-ci -e CONNECT_ON_STARTUP=false -e MINIO_ENABLED=false \
  -e AMQP_GLOBAL_ENABLED=false -e AMQP_URL= -e WEBHOOK_URL= -e WADEBUG=ERROR "$TEST_IMAGE" >/dev/null
python3 scripts/container_lifecycle.py wait "$app"
port="$(docker port "$app" 8080/tcp | awk -F: 'NR==1{print $NF}')"
python3 scripts/probe.py "http://127.0.0.1:$port" go
