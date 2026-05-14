#!/usr/bin/env bash
# HIWALOY demo launcher (macOS / Linux)
#
# Why this script exists:
#   The frontend uses a Next.js dynamic route `app/history/[id]/page.tsx`.
#   Docker BuildKit on some platforms (notably Windows / certain BuildKit
#   versions) treats the `[id]` directory name as a glob character class
#   while resolving the build context, producing the error:
#       invalid file request app/history/[id]/page.tsx
#   Falling back to the legacy builder avoids the glob expansion.

set -euo pipefail

echo "[HIWALOY] Disabling Docker BuildKit (workaround for [id] dynamic route)..."
export DOCKER_BUILDKIT=0
export COMPOSE_DOCKER_CLI_BUILD=0

if [ ! -f ".env" ]; then
    echo "[HIWALOY] No .env found — copying .env.example to .env (DEMO_MODE=true)"
    cp .env.example .env
fi

echo "[HIWALOY] Starting docker compose..."
docker compose up --build
