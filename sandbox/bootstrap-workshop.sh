#!/bin/bash
# Shared bootstrap: stage the workshop, mint a learner-scoped LiteLLM key, bridge env into /root/.bashrc,
# and start the stack (Temporal dev server, mock finance API, control panel, test UI, mitmproxy).
#
# Called from BOTH track_scripts/setup-workshop and every challenge setup-workshop. Instruqt's per-challenge
# Preview skips track-level scripts, so each challenge must be able to bootstrap on its own. The sentinel
# makes repeat calls a no-op.
set -euo pipefail

SENTINEL=/root/.workshop-bootstrapped
[ -f "$SENTINEL" ] && exit 0

for _ in $(seq 1 600); do [ -f /opt/instruqt/bootstrap/host-bootstrap-completed ] && break; sleep 1; done
[ -f /opt/instruqt/bootstrap/host-bootstrap-completed ] || { echo "ERROR: Instruqt host bootstrap did not finish in 10 minutes." >&2; exit 1; }

SECRET_BROKER_BASE_URL="${SECRET_BROKER_BASE_URL:-https://tmprl-dem-cld-secret-broker-429214323166-us-west-1.s3.us-west-1.amazonaws.com/secret-broker}"
SECRET_BROKER_VERSION="${SECRET_BROKER_VERSION:-main}"
LITELLM_KEY_DURATION="${LITELLM_KEY_DURATION:-1d}"
LITELLM_MAX_BUDGET="${LITELLM_MAX_BUDGET:-5}"
LITELLM_ENV_FILE=/root/.litellm-env
LITELLM_PROXY_HOST="${LITELLM_PROXY_HOST:-litellm-instruqt.tmprl-demo.cloud}"
export INSTRUQT_BROKER_URL="${INSTRUQT_BROKER_URL:-https://litellm-broker-instruqt.tmprl-demo.cloud}"
export INSTRUQT_BROKER_KEY_ID="${INSTRUQT_BROKER_KEY_ID:-v1}"
export INSTRUQT_LITELLM_TRACK_ID="${INSTRUQT_LITELLM_TRACK_ID:-${INSTRUQT_TRACK_SLUG:-durable-finance-research-agent}}"

mint_litellm_token() {
    if [ -z "${TEMPORAL_LITELLM_BROKER_SECRET:-}" ]; then
        echo "ERROR: TEMPORAL_LITELLM_BROKER_SECRET is not set. Configure the Instruqt secret before starting the track." >&2
        exit 1
    fi
    curl --fail --silent --show-error --location --retry 10 --retry-all-errors --retry-delay 2 \
        --retry-max-time 60 --connect-timeout 10 \
        "${SECRET_BROKER_BASE_URL}/${SECRET_BROKER_VERSION}/install.sh" --output /tmp/install-secret-broker.sh
    SECRET_BROKER_BASE_URL="${SECRET_BROKER_BASE_URL}" SECRET_BROKER_VERSION="${SECRET_BROKER_VERSION}" \
        sh /tmp/install-secret-broker.sh
    export TEMPORAL_LITELLM_BROKER_SECRET
    secret-broker litellm --duration="${LITELLM_KEY_DURATION}" --budget="${LITELLM_MAX_BUDGET}"
    set -a; . "${LITELLM_ENV_FILE}"; set +a
}

# 1. Stage a writable copy. The venv stays at /opt/workshop/.venv (shared, read-only by convention).
mkdir -p /root/workshop
tar -C /opt/workshop --exclude=.venv -cf - . | tar -C /root/workshop -xf -

# 1b. Start code-server (the Exercise tab) first and never gate it on anything else. Port 8080, not 8443.
EDITOR_FOLDER=/root/workshop
if ! curl -sf -o /dev/null "http://127.0.0.1:8080/" 2>/dev/null; then
    nohup code-server --bind-addr "0.0.0.0:8080" --auth none --disable-telemetry --disable-update-check \
        --user-data-dir /root/.cs-workshop "${EDITOR_FOLDER}" > /tmp/code-server-8080.log 2>&1 &
    disown || true
fi

# 2. Mint the key unless one was supplied (local Docker testing). The broker writes OpenAI-style variables;
#    map them to the names the workshop code reads.
if [ -z "${LITELLM_API_KEY:-}" ]; then
    mint_litellm_token
fi
export LITELLM_API_KEY="${LITELLM_API_KEY:-${OPENAI_API_KEY:-}}"
export LITELLM_API_BASE="${LITELLM_API_BASE:-${OPENAI_BASE_URL:-${OPENAI_API_BASE:-https://${LITELLM_PROXY_HOST}}}}"
export MODEL_ID="${MODEL_ID:-gpt-4o}"
if [ -z "${LITELLM_API_KEY}" ]; then
    echo "ERROR: the broker did not provide an API key. Variable names in ${LITELLM_ENV_FILE}:" >&2
    sed -E 's/=.*//' "${LITELLM_ENV_FILE}" >&2 || true
    exit 1
fi

# 3. Bridge env into the attendee's shell. /root/.bashrc, never Docker ENV (see the Dockerfile).
cat >> /root/.bashrc <<BASHRC
export LITELLM_API_KEY="${LITELLM_API_KEY}"
export LITELLM_API_BASE="${LITELLM_API_BASE}"
export MODEL_ID="${MODEL_ID}"
export TEMPORAL_UI_URL=""
export TEMPORAL_ADDRESS="127.0.0.1:7233"
export UV_PROJECT_ENVIRONMENT=/opt/workshop/.venv
export UV_NO_SYNC=1
export PATH="/opt/workshop/.venv/bin:/root/.temporalio/bin:\$PATH"
export HTTP_PROXY="http://127.0.0.1:8888"
export HTTPS_PROXY="http://127.0.0.1:8888"
export NO_PROXY="127.0.0.1,localhost"
export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
BASHRC

# 4. Start the stack. dev.py reads LITELLM_API_BASE, so the proxy blocks the real gateway host.
#    Run it WITHOUT the proxy env so Temporal health checks and the UI stay direct.
cd /root/workshop
env -u HTTP_PROXY -u HTTPS_PROXY TEMPORAL_UI_URL="" BIND_HOST=0.0.0.0 UV_PROJECT_ENVIRONMENT=/opt/workshop/.venv UV_NO_SYNC=1 \
    PATH="/opt/workshop/.venv/bin:/root/.temporalio/bin:$PATH" \
    uv run python scripts/dev.py up > /tmp/stack.log 2>&1 || { cat /tmp/stack.log >&2; exit 1; }

# 5. Wait for the editor workbench (not just the listener). Never fatal.
code_server_ready() {
    [ "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 "http://127.0.0.1:8080/?folder=${EDITOR_FOLDER}" 2>/dev/null)" = "200" ] \
        && grep -q "Extension host agent started" /tmp/code-server-8080.log 2>/dev/null
}
for _ in $(seq 1 90); do code_server_ready && break; sleep 1; done
code_server_ready || echo "==> WARNING: code-server 8080 not ready." >&2

touch "$SENTINEL"
echo "==> Workshop bootstrap complete."
