# Sandbox image for the Durable Finance Research Agent workshop.
# Bakes in: Python 3.12 + uv, Temporal CLI, just, code-server, the workshop source at /opt/workshop,
# and one pre-warmed uv venv (Strands, Temporal plugin, FastAPI, mitmproxy) at /opt/workshop/.venv.
#
# Build context is the repo root:  docker build --platform linux/amd64 -f sandbox/Dockerfile .
# The same image backs Instruqt and `just up-docker`.

FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive PYTHONUNBUFFERED=1

# 1. System packages
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates git procps vim jq \
    && rm -rf /var/lib/apt/lists/*

# 2. uv, just, Temporal CLI
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
RUN curl -sSf https://just.systems/install.sh | bash -s -- --to /usr/local/bin
RUN curl -sSf https://temporal.download/cli.sh | sh
ENV PATH="${PATH}:/root/.temporalio/bin"

# 3. code-server (the Exercise tab). track_scripts/setup-workshop starts it on 8080.
ARG CODE_SERVER_VERSION=4.96.4
RUN curl -fsSL https://code-server.dev/install.sh | sh -s -- --version ${CODE_SERVER_VERSION}
# Workspace Trust must be off or code-server shows a blank page. autoSave is load-bearing: assignments
# tell learners the editor saves as they type.
RUN mkdir -p /root/.cs-workshop/User && printf '%s\n' \
      '{' \
      '    "security.workspace.trust.enabled": false,' \
      '    "workbench.colorTheme": "Default Dark+",' \
      '    "workbench.startupEditor": "none",' \
      '    "workbench.editor.enablePreview": false,' \
      '    "editor.fontSize": 14,' \
      '    "editor.minimap.enabled": false,' \
      '    "files.autoSave": "afterDelay",' \
      '    "files.autoSaveDelay": 300,' \
      '    "telemetry.telemetryLevel": "off",' \
      '    "explorer.compactFolders": false,' \
      '    "files.exclude": { "**/.venv": true, "**/__pycache__": true, "**/uv.lock": true, "**/.pytest_cache": true }' \
      '}' > /root/.cs-workshop/User/settings.json
RUN code-server --user-data-dir /root/.cs-workshop --install-extension detachhead.basedpyright \
    && code-server --user-data-dir /root/.cs-workshop --install-extension charliermarsh.ruff \
    || echo "==> WARNING: a code-server extension did not install; the editor still works without it."

# 4. Workshop source and one shared venv. Learners get a writable copy at /root/workshop (bootstrap).
WORKDIR /opt/workshop
COPY pyproject.toml uv.lock justfile .env.example ./
COPY scripts/ scripts/
COPY shared/ shared/
COPY modules/ modules/
RUN uv sync --frozen

# 5. mitmproxy CA: generate once, trust it system-wide so proxied HTTPS calls succeed.
RUN (/opt/workshop/.venv/bin/mitmdump --listen-port 8889 >/dev/null 2>&1 &) ; sleep 6; pkill -f '[m]itmdump' || true; \
    cp /root/.mitmproxy/mitmproxy-ca-cert.pem /usr/local/share/ca-certificates/mitmproxy-ca.crt \
    && update-ca-certificates

# Pre-warm the Temporal test server the offline tests download on first use (time-skipping env), so a learner's
# first `just test` does not need the network.
RUN /opt/workshop/.venv/bin/python scripts/prewarm_test_server.py || true

# 6. Shared bootstrap, called from the track setup and from every challenge setup (Instruqt's per-challenge
# Preview skips track-level scripts; the sentinel file makes repeat calls a no-op).
COPY sandbox/bootstrap-workshop.sh /opt/bootstrap-workshop.sh
RUN chmod +x /opt/bootstrap-workshop.sh

# Proxy and LLM env vars are NOT Docker ENV. A container-wide HTTP(S)_PROXY would route Instruqt's own agent
# through mitmproxy and break the terminal and editor tabs. bootstrap appends them to /root/.bashrc instead.
WORKDIR /root

# Keep PID 1 alive. Without a CMD the container exits and every tab returns HTTP 572.
CMD ["sleep", "infinity"]
