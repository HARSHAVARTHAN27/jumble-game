# Render and Vercel deployment

Live checks confirmed that `https://jumble-game-f00r.onrender.com/health` returns HTTP 200 with `database: ready`, but the backend reports `environment: development`. Its CORS preflight rejects `https://jumble-game-sooty.vercel.app` with HTTP 400 and no allowed-origin header. The deployed frontend already includes the correct Render API origin. Direct Vercel `/control` navigation currently returns HTTP 404.

For this deployment, set Render `FRONTEND_URL=https://jumble-game-sooty.vercel.app`, `ENVIRONMENT=production`, and, after deploying the cookie configuration change, `PLAYER_COOKIE_SAMESITE=none`. Keep Vercel `VITE_API_URL=https://jumble-game-f00r.onrender.com`. Deploy `frontend/vercel.json` with the Vercel root directory set to `frontend` to fix direct routes. Changing the local files alone does not update dashboard variables.

## Render backend

Use a Python **Web Service** with these settings (the root `render.yaml` also supplies a Blueprint):

- Root directory: `backend`
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health check path: `/health`

Set these in Render Environment; the local ignored `.env` is not deployed:

| Variable | Value |
|---|---|
| `ENVIRONMENT` | `production` |
| `FRONTEND_URL` | Exact HTTPS Vercel production origin, no path or trailing slash |
| `SUPABASE_URL` | Existing project's Supabase URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Existing project's server secret/service-role key; backend only |
| `SUPABASE_ANON_KEY` | Existing project's public key |
| `DATABASE_URL` | Same project's PostgreSQL session-pooler connection URL, with the actual URL-encoded database password |
| `AUTO_MIGRATE` | `true` |
| `PLAYER_COOKIE_SAMESITE` | `none` for separate Vercel/Render domains; `lax` for the existing same-site/proxy setup |

Automatic migration requires the PostgreSQL connection string. A Supabase API key or host login password cannot replace it. The session pooler is appropriate if the direct database hostname is unreachable from the deployment's network. Keep the complete `backend/sql/migrations` directory in the deployment. If you already manage SQL manually, `AUTO_MIGRATE=false` is supported, but the schema must contain all existing migrations; disabling migration does not create missing tables.

Redeploy and open your Render origin plus `/health`. A working, initialized deployment returns `status: healthy` and `database: ready`. If the process never starts, inspect the first traceback in Render Logs: missing environment variables, a PostgreSQL connection failure, or the wrong module/start directory are separate problems.

## Vercel frontend

Use root directory `frontend`, Vite framework, build `npm run build`, output `dist`. `frontend/vercel.json` restores SPA routes such as `/control` and `/game` on direct navigation.

If the existing Vercel project uses the repository root instead, the root `vercel.json` installs/builds `frontend` and serves `frontend/dist` with the same SPA rewrite. Deploy the configuration file corresponding to the configured root directory; a file under `frontend` is not used by a repository-root deployment.

Set the following Vercel environment variables and redeploy; Vite embeds them at build time:

- `VITE_API_URL`: the Render **HTTPS origin only**, with no `/api` suffix. Requests already include `/api` in their paths.
- `VITE_SUPABASE_URL`: the same Supabase project URL.
- `VITE_SUPABASE_PUBLISHABLE_KEY` or `VITE_SUPABASE_ANON_KEY`: public key only.
- `VITE_DEMO=false`.

If `VITE_API_URL` is omitted, the app falls back to `http://localhost:8000`, which targets each visitor's computer. Never place the Supabase service-role key or database URL in Vercel browser variables.

`FRONTEND_URL` on Render must match the origin you open in the browser; production and preview Vercel deployment URLs are different origins. This affects both CORS and the existing authenticated WebSocket Origin check.

Player sign-in uses an HttpOnly cookie. Separate `vercel.app` and `onrender.com` origins require secure `SameSite=None` cookies, supplied by the Render Blueprint. Browsers that block third-party cookies can still prevent cross-site player sessions; use frontend/backend custom domains under the same parent domain or the project's documented same-origin proxy approach for those browsers. The existing REST recovery and WebSocket architecture remain unchanged.

## Checking a failed deployment

1. Render `/health` unreachable: inspect build/startup logs and start command/environment.
2. `/health` reports a database problem: verify matching Supabase keys, schema and database connection settings.
3. Render `/health` is ready but Vercel cannot reach it: check the built `VITE_API_URL`, HTTPS and Render `FRONTEND_URL`.
4. Host works but player state returns 403: check production cookie settings and browser third-party-cookie policy.

Follow-up checks confirmed production mode and passing CORS, but an existing player's join response still returned `SameSite=lax; Secure`. Replaying the returned cookie restored player state with HTTP 200, isolating the browser's cross-site cookie restriction. Deploy the updated `backend/app/config.py` and `backend/app/routers/employee.py` with `PLAYER_COOKIE_SAMESITE=none`, then rejoin to obtain a fresh cookie. The existing host account still has `app_metadata.role=host`; host sign-in requires a valid Supabase Bearer token independently of the player cookie.

The updated configuration now defaults to `SameSite=None` automatically outside development. An explicit `PLAYER_COOKIE_SAMESITE=lax` or `strict` still overrides it: remove that override or set it to `none` for this Render/Vercel deployment. Check the join response's Set-Cookie attributes, not only `/health`: it must include `SameSite=none; Secure`. Firefox's reported rejection of a Lax cookie confirms why subsequent player requests have no session cookie.

These files prepare deployment but do not update existing Render or Vercel dashboard settings. Apply the settings above and redeploy the changed repository. Exact diagnosis needs the live URLs and the failed Render deployment's log.

References: [Render FastAPI deployment](https://render.com/docs/deploy-fastapi), [Vercel Vite deployment](https://vercel.com/docs/frameworks/frontend/vite).

## Intermittent Supabase read failures

If Render logs show `httpcore/_sync/http2.py` followed by `ReadError: [Errno 11] Resource temporarily unavailable`, deploy the updated backend database client. It supplies a shared HTTP/1.1 transport to Supabase, bounded connection timeouts, and one retry for interrupted GET/HEAD reads. Writes and RPCs are not replayed after read failures. Persistent transport failures return HTTP 503 with `DATABASE_UNAVAILABLE`; host authentication transport failures retain this temporary status rather than reporting invalid credentials.

This change requires redeploying the backend code; no new environment variable or frontend build is required. After deployment, check player state and host requests in addition to `/health`, and inspect Render logs for recurring transport failures.
