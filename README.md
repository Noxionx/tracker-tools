# Tracker Tools API

Tracker Tools API is a FastAPI service designed to make private tracker automation safer.

It helps you decide whether a torrent should be admitted before sending it to Transmission, based on projected ratio impact and disk usage constraints.

## Introduction

Tracker Tools was created to solve a practical issue with private tracker automation.

Most private trackers require a minimum ratio to keep download access. In practice, many users rely on tools like autobrr + RSS feeds to catch newly published torrents (especially freeleech ones) and build upload through early seeding.

That approach is fast, but usually not context-aware. It does not reason about your real ratio reserve or your available disk headroom before accepting new torrents. During high-volume tracker activity, this can lead to two concrete failures:
- Ratio safety illusion: a ratio value alone can hide risk. A ratio of 2.0 with 20 GB down / 10 GB up is not the same operationally as 20 TB down / 10 TB up.
- Storage pressure: aggressive auto-grabbing can saturate disk very quickly.

Tracker Tools closes that gap with an admission API built for decision-making, not just automation speed. Before adding a torrent, it forecasts ratio and storage impact, then returns an explicit allow/deny decision based on configurable rules.

In short, this project turns torrent intake from blind automation into policy-driven admission control.

## What It Does

- Scrapes tracker statistics (ratio, uploaded/downloaded, bonus).
- Forecasts torrent admission impact on ratio and storage.
- Admits torrents through Transmission RPC only when constraints are satisfied.
- Purges torrents based on ratio and/or lifetime criteria.
- Persists state in SQLite by default (or another SQLAlchemy-compatible database URL).

## Features

- Modern FastAPI structure with routers and service layer separation.
- Async SQLAlchemy integration.
- Background scheduler for periodic tracker refresh.
- Configurable thresholds from environment variables.
- Integration and unit tests with pytest.

## Quick Start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install
uvicorn main:app --reload --port 8679
```

Then open `http://localhost:8679/docs`.

## Tech Stack

- Python 3.12+
- FastAPI
- SQLAlchemy (async)
- APScheduler
- Playwright (tracker scraping)
- Transmission RPC client
- pytest / pytest-asyncio

## Project Structure

```text
app/
  api/
    routes/
      debug.py
      storage.py
      system.py
      torrents.py
      trackers.py
    dependencies.py
  core/
    config.py
    exceptions.py
    files.py
    logging.py
    time.py
  db/
    base.py
    session.py
  models/
    tracker.py
  schemas/
    storage.py
    torrent.py
    tracker.py
  scrapers/
    c411.py
    torr9.py
  services/
    purge_service.py
    scheduler_service.py
    scraper_service.py
    storage_service.py
    torrent_service.py
    tracker_domain.py
    tracker_registry.py
    tracker_stats_service.py
    transmission_service.py
  main.py

main.py                # Runtime entrypoint exposing FastAPI app
tests/                 # Unit + integration tests
requirements.txt
pytest.ini
```

## Installation

1. Create and activate a virtual environment.
2. Install dependencies.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

3. Install browser binaries for Playwright:

```bash
playwright install
```

4. (Optional) create a `.env` file for your runtime configuration.

## Configuration

Create a `.env` file at the repository root.

### Core

- `DATABASE_URL`: Optional full SQLAlchemy URL.
- `CONFIG_DIR`: Config directory for generated files (default: `.config`).
- `REFRESH_INTERVAL_MINUTES`: Tracker refresh interval (default: `60`).
- `MAX_TRACKER_STATS_AGE_MINUTES`: Max age before forced refresh (default: `120`).

### Transmission

- `TRANSMISSION_HOST` (default: `localhost`)
- `TRANSMISSION_PORT` (default: `9091`)
- `TRANSMISSION_PATH` (default: `/transmission/rpc`)
- `TRANSMISSION_USERNAME` (optional)
- `TRANSMISSION_PASSWORD` (optional)

### Admission / Storage

- `DEFAULT_MIN_RATIO` (default: `1.0`)
- `{TRACKER}_MIN_RATIO` (example: `C411_MIN_RATIO`)
- `MAX_STORAGE_BYTES` (default: `0`, disabled)
- `MIN_FREE_STORAGE_BYTES` (default: `0`, disabled)
- `DOWNLOAD_DIR` (optional)

### Scrapers

- C411 credentials:
  - `C411_USER`
  - `C411_PASS`
- Torr9 credentials (supports aliases):
  - `TORR9_USER` or `TOR9_USER`
  - `TORR9_PASSWORD` or `TORR9_PASS` or `TOR9_PASS`

Example `.env` snippet:

```env
DEFAULT_MIN_RATIO=1.1
MAX_STORAGE_BYTES=1500000000000
MIN_FREE_STORAGE_BYTES=50000000000
TRANSMISSION_HOST=localhost
TRANSMISSION_PORT=9091
```

## Run

### Development

```bash
uvicorn main:app --reload --port 8679
```

### Production-style (example)

```bash
uvicorn main:app --host 0.0.0.0 --port 8679
```

## Docker

The repository includes a cloud-native container image definition in [Dockerfile](Dockerfile):
- non-root runtime user
- healthcheck endpoint probing
- Playwright Chromium runtime installed
- explicit volumes for persistent config and downloaded data

### Build the image

```bash
docker build -t tracker-tools:local .
```

### Run with environment variables

```bash
docker run --rm -p 8679:8679 \
  -e DEFAULT_MIN_RATIO=1.2 \
  -e TRANSMISSION_HOST=transmission \
  -e TRANSMISSION_PORT=9091 \
  tracker-tools:local
```

### Run with mounted config and data

```bash
docker run --rm -p 8679:8679 \
  -v $(pwd)/runtime-config:/config \
  -v $(pwd)/downloads:/app/downloads \
  -e CONFIG_DIR=/config \
  -e DOWNLOAD_DIR=/app/downloads \
  tracker-tools:local
```

Notes:
- `CONFIG_DIR` stores scraper state files and (by default) the local SQLite DB.
- In orchestration environments, prefer secrets/env injection and persistent volume mounts.
- Health endpoint is available on `GET /` and used by the container healthcheck.

## API Overview

Interactive OpenAPI docs are available at `/docs` when the application is running.

### System

- `GET /` : health/basic discovery
- `GET /trackers` : available scraper names

### Tracker Stats

- `GET /ratios`
- `GET /trackers/{tracker}/stats`
- `GET /trackers/{tracker}/history?limit=100`
- `POST /trackers/{tracker}/refresh`

### Torrent Management

- `GET /torrents`
- `POST /torrents/forecast`
- `POST /torrents/admit`
- `POST /torrents/purge`

### Storage / Debug

- `GET /storage`
- `GET /debug/latest-snapshots`

## Request Examples

### Forecast (minimal payload)

`min_ratio` and `max_storage_bytes` are optional and use defaults when omitted.

```json
{
  "tracker": "c411",
  "torrent": "magnet:?xt=urn:btih:..."
}
```

### Admit (minimal payload)

```json
{
  "tracker": "torr9",
  "torrent": "magnet:?xt=urn:btih:..."
}
```

### Purge

At least one of `target_ratio` or `max_lifetime_hours` is required.

```json
{
  "tracker": "c411",
  "target_ratio": 2.0,
  "dry_run": true,
  "delete_data": false
}
```

## Testing

Run all tests:

```bash
pytest -q
```

Test strategy includes:
- Unit tests for deterministic domain logic.
- Service-level tests for admission and purge workflows (success, dry-run, and failure paths).
- API integration tests with:
  - Isolated SQLite database per test run.
  - FastAPI dependency overrides.
  - HTTPX ASGI transport against the FastAPI app.
  - Targeted monkeypatching for external boundaries.
  - Request validation checks (HTTP 422) for required fields.

Recommended test commands:

```bash
pytest -q
pytest -q tests/test_api_integration.py
pytest -q tests/test_torrent_service.py tests/test_purge_service.py
```

Optional coverage run:

```bash
pytest --cov=app --cov-report=term-missing
```

## GitHub Actions CI/CD

Workflow definitions:
- CI: [.github/workflows/ci.yml](.github/workflows/ci.yml)
- Release: [.github/workflows/release.yml](.github/workflows/release.yml)

Jobs:
- CI workflow:
  - `tests`: dependency installation and pytest execution.
  - `docker-build-validation`: Docker build validation without push.
- Release workflow:
  - `verify-version`: validates that git tag version matches `app_version` in [app/core/config.py](app/core/config.py).
  - `tests`: full test suite before publication.
  - `publish-dockerhub`: image build/push to Docker Hub.
  - `publish-gcr`: image build/push to Google Container Registry (`gcr.io`).
  - `github-release`: creates a GitHub Release with generated notes.

Execution model:
- Pull requests: run CI only (`tests` + `docker-build-validation`).
- Pushes on branches: run CI only.
- Pushes on version tags (`v*`): run release workflow.

Published tags for Docker Hub and GCR (release workflow):
- short commit SHA
- git tag name (for tag pipelines)
- `latest` on tag release

Release command example:

```bash
git tag v1.0.0
git push origin v1.0.0
```

Important: if `app_version` is `1.0.0` in [app/core/config.py](app/core/config.py), the tag must be `v1.0.0`.

### Required GitHub Repository Variables

- `DOCKERHUB_IMAGE`: full Docker Hub image name (example: `myuser/tracker-tools`)
- `GCP_PROJECT_ID`: Google Cloud project ID
- `GCR_IMAGE_NAME`: image repository name in GCR (example: `tracker-tools`)

### Required GitHub Repository Secrets

- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`
- `GCP_SA_KEY` (JSON key for a service account with permission to push to GCR)

If Docker Hub or GCR variables/secrets are missing, publish jobs are automatically skipped.

## Architecture Notes

- `api/routes`: HTTP contract and request/response mapping.
- `schemas`: Pydantic request/response models.
- `services`: Business logic and integration orchestration.
- `db/models`: Persistence and SQLAlchemy entities.
- `scrapers`: Tracker-specific adapters.

This layered design keeps business rules testable and endpoints thin.

## Project Status

Current state:
- Refactored FastAPI architecture with clear separation of concerns.
- Production-ready container build.
- GitHub Actions pipeline for tests, Docker build validation, and registry publishing.
- Unit, service, and API integration test layers in place.

## Next Hardening Steps

- Add migration tool (Alembic) for schema evolution.
- Add structured observability (JSON logs, request IDs, metrics).
- Add contract tests for endpoint payload compatibility.
