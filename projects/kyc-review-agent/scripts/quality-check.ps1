$ErrorActionPreference = "Stop"

uv run ruff check src tests
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

uv run pytest
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
