# HIWALOY demo launcher (Windows / PowerShell)
#
# Why this script exists:
#   The frontend uses a Next.js dynamic route `app/history/[id]/page.tsx`.
#   Docker BuildKit on Windows treats the `[id]` directory name as a glob
#   character class while resolving the build context, producing the error:
#       invalid file request app/history/[id]/page.tsx
#   Falling back to the legacy builder avoids the glob expansion.

$ErrorActionPreference = "Stop"

Write-Host "[HIWALOY] Disabling Docker BuildKit (workaround for [id] dynamic route)..." -ForegroundColor Cyan
$env:DOCKER_BUILDKIT = "0"
$env:COMPOSE_DOCKER_CLI_BUILD = "0"

if (-not (Test-Path ".env")) {
    Write-Host "[HIWALOY] No .env found — copying .env.example to .env (DEMO_MODE=true)" -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
}

Write-Host "[HIWALOY] Starting docker compose..." -ForegroundColor Cyan
docker compose up --build
