# Durable Finance Research Agent. Sample data only, not financial advice.
# VARIANT=solution runs the finished code instead of your exercise.
set dotenv-load := true
set positional-arguments := true
variant := env_var_or_default("VARIANT", "exercise")
m1 := "modules/01-strands-agent-basics/" + variant
m2 := "modules/02-strands-finance-research-agent/" + variant
m3 := "modules/03-durable-strands-agent/" + variant

default:
    @just --list

doctor:
    uv run python scripts/dev.py doctor

up:
    uv sync
    uv run python scripts/dev.py up

down:
    uv run python scripts/dev.py down

status:
    uv run python scripts/dev.py status

# Module 1 and 2: run the agent once. Example: just m1 "Price moved 98.2 to 112.4, percent change?"
m1 *prompt:
    uv run python scripts/dev.py exec --cwd {{m1}} -- python run.py "$@"

m2 *prompt:
    uv run python scripts/dev.py exec --cwd {{m2}} -- python run.py "$@"

# Module 3: worker in one terminal, start in another.
worker:
    uv run python scripts/dev.py exec --cwd {{m3}} -- python worker.py

start *prompt:
    uv run python scripts/dev.py exec --cwd {{m3}} -- python start.py "$@"

# Short approval window (30 s) to watch the timeout escalate.
start-short *prompt:
    uv run python scripts/dev.py exec --cwd {{m3}} -- python start.py --approval-timeout 30 "$@"

approve id:
    uv run python scripts/dev.py exec --cwd {{m3}} --no-proxy -- python decide.py approve {{id}}

reject id:
    uv run python scripts/dev.py exec --cwd {{m3}} --no-proxy -- python decide.py reject {{id}}

# Offline tests, no server or key needed. Example: just test 3
test n="3":
    cd modules/0{{n}}-*/{{variant}} && uv run --project ../../.. python -m pytest -q

# Self-paced with Docker: same image as Instruqt. Needs .env with LITELLM_API_BASE and LITELLM_API_KEY.
up-docker:
    docker compose up -d --build
    @echo "UI http://localhost:8000  Panel http://localhost:5050  Temporal UI http://localhost:8233"
    @echo "Run modules inside the container: docker compose exec workshop bash"

down-docker:
    docker compose down

# ---- Instruqt track authoring (needs the Instruqt CLI and `instruqt auth login`) ----

# Register the slug server-side (run ONCE, before the first push). The track starts in maintenance mode.
create:
    #!/usr/bin/env bash
    set -euo pipefail
    slug=$(grep -E '^slug:' instruqt/track.yml | head -1 | awk '{print $2}' | tr -d '"')
    title=$(grep -E '^title:' instruqt/track.yml | head -1 | sed -E 's/^title:[[:space:]]*//' | sed -E 's/^"(.*)"$/\1/')
    tmp=$(mktemp -d)
    (cd "$tmp" && instruqt track create "$slug" --title "$title")
    rm -rf "$tmp"
    echo "Registered slug '$slug' (maintenance mode). Next: 'just push' (use --force on the first push)."

push:
    cd instruqt && instruqt track push

pull:
    cd instruqt && instruqt track pull

validate:
    cd instruqt && instruqt track validate

diff:
    cd instruqt && instruqt track diff

# Learner simulator through every challenge (runs the solve scripts). Not the pytest suite.
track-test:
    cd instruqt && instruqt track test
