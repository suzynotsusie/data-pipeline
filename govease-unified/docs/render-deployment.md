# Durable Render Deployment

## Reproducible runtime

- `.python-version` and `PYTHON_VERSION` both pin Python 3.12.11.
- `pyproject.toml` defines direct production dependencies.
- `uv.lock` locks the complete dependency graph.
- Render runs `uv sync --frozen --no-dev`; dependency drift makes the build fail instead of silently changing production.

After changing dependencies, update and test the lockfile intentionally:

```powershell
uv lock --upgrade-package <package>
uv sync --frozen --no-dev
python -m unittest discover -v
```

## Startup and index lifecycle

The start command only launches Uvicorn. FastAPI schedules index initialization in a background thread during lifespan startup, so an embedding outage cannot prevent port binding.

- `/api/v1/health`: process liveness; use as Render health check.
- `/api/v1/ready`: procedure data, active collection, chunk count and index state.
- `degraded` or `failed`: API remains available, but vector retrieval falls back to deterministic local retrieval.

An index is named from its data fingerprint. A new collection becomes active only after embeddings are upserted and the Chroma count matches the expected chunk count. The atomic manifest preserves the previous active collection if a rebuild fails.

## First redeploy after the Chroma migration

1. Confirm the Render service runtime is Python 3.
2. Sync the Blueprint or set `PYTHON_VERSION=3.12.11` in the Dashboard.
3. Set `OPENAI_API_KEY` and `GOVEASE_AUTO_INITIALIZE_INDEX=true`. The Blueprint already
   declares the production Vercel origin in `CORS_ORIGINS`; add any preview or custom
   domains explicitly as comma-separated HTTPS origins.
4. Use **Clear build cache & deploy** once to remove the old Python 3.14 environment.
5. Wait for `/api/v1/ready` to report `components.index.status=ready`.
6. `CHROMA_PATH=/var/data/chroma_v1` intentionally uses a fresh directory so Chroma 1.5.9 never opens the old 0.5.5 on-disk schema. Keep `/var/data/chroma_db` temporarily for rollback and remove it only during a later controlled maintenance window.

Do not move ingestion into Render's build or pre-deploy command: attached persistent disks are only available to the runtime instance.

## Verify browser access

After every frontend-domain change, verify the CORS preflight before testing the UI:

```powershell
curl.exe -i -X OPTIONS "https://govease-ai.onrender.com/api/v1/intake" `
  -H "Origin: https://gov-ease-ai.vercel.app" `
  -H "Access-Control-Request-Method: POST" `
  -H "Access-Control-Request-Headers: content-type"
```

The response must include `access-control-allow-origin: https://gov-ease-ai.vercel.app`.
