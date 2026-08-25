#!/usr/bin/env bash
#
# One-command setup + run for the Art Manager agent (Ubuntu / Linux / macOS).
#
#   ./run.sh           # install deps on first run, then run the daily workflow
#   ./run.sh --tests   # run the test suite instead
#   ./run.sh --setup   # only create the venv + install deps, don't run
#
# On first run this creates a local virtualenv in .venv and installs
# dependencies; later runs reuse it and start immediately.
#
# Requires Python 3.12 or 3.13 — the nooa runtime does not support 3.11 or 3.14+.
set -euo pipefail
cd "$(dirname "$0")"

VENV=".venv"
PYBIN="$VENV/bin/python"

# Find an interpreter nooa supports (3.12 or 3.13).
find_python() {
    local cand ver
    for cand in python3.13 python3.12 python3 python; do
        command -v "$cand" >/dev/null 2>&1 || continue
        ver=$("$cand" -c 'import sys; print("%d.%d" % sys.version_info[:2])' 2>/dev/null) || continue
        case "$ver" in
            3.12 | 3.13)
                echo "$cand"
                return 0
                ;;
        esac
    done
    return 1
}

# Create the venv and install dependencies if we don't have one yet.
if [ ! -x "$PYBIN" ]; then
    if ! PY=$(find_python); then
        echo "ERROR: need Python 3.12 or 3.13 (nooa does not support 3.11 or 3.14+)." >&2
        echo "  Ubuntu 24.04 ships 3.12. On 22.04 or older, install it with:" >&2
        echo "    sudo apt update && sudo apt install -y python3.12 python3.12-venv" >&2
        exit 1
    fi
    echo ">> creating virtualenv with $PY in $VENV"
    "$PY" -m venv "$VENV"
    "$PYBIN" -m pip install --quiet --upgrade pip
    echo ">> installing dependencies (first run only)"
    "$PYBIN" -m pip install --quiet -r requirements-dev.txt
fi

case "${1:-}" in
    --setup)
        echo ">> setup complete."
        exit 0
        ;;
    --tests)
        exec "$PYBIN" -m pytest -q
        ;;
esac

# The agent needs a key to call the model. Accept either a .env file (loaded
# automatically) or a real environment variable.
if [ ! -f .env ] && [ -z "${ANTHROPIC_API_KEY:-}" ]; then
    echo "ERROR: no Anthropic API key found." >&2
    echo "  Add one with:" >&2
    echo "    read -rsp 'Anthropic API key: ' K && printf 'ANTHROPIC_API_KEY=%s\\n' \"\$K\" > .env && unset K" >&2
    exit 1
fi

exec "$PYBIN" -m agents.run_daily
