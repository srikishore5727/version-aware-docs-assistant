# Deployment

VADA is a long-running FastAPI process with two local indexes (SQLite FTS5 and
Chroma) plus a feedback database. It needs a **persistent process with a writable
disk**, not a serverless function, so it ships as a Docker image.

- **Platform:** Render, free plan, `singapore` region, built from `Dockerfile`.
- **Live:** <https://vada-nds8.onrender.com>
- **Blueprint:** `render.yaml` at the repository root.
- **Health check:** `/health`.
- **Auto-deploy:** on every push to `main`.

## Why not Vercel

Vercel runs serverless functions, not containers. That fails this app in four
concrete ways:

| Vercel behaviour | Effect on VADA |
| --- | --- |
| Read-only filesystem except `/tmp`; `/tmp` is per-instance | `data/index/vada.db`, `data/index/chroma`, and `data/feedback.db` cannot be kept. Search and feedback reset between requests. |
| Bundle size limits (~250 MB) | `chromadb` with numpy and tokenizers is heavy before application code is added. |
| No persistent process | Every cold start would re-embed all 60 chunks through Gemini: slow, and it spends API calls. |
| No Docker support | The production image cannot be deployed as-is. |

Making Vercel work would mean replacing both stores with hosted services. That is
a different architecture, not a deployment choice.

## One-time setup

Prerequisites: a GitHub account (the repository is already there) and a Gemini
API key.

1. Open <https://dashboard.render.com/blueprints> and sign in with GitHub.
2. Choose **New Blueprint Instance**, then select
   `srikishore5727/version-aware-docs-assistant`.
3. Render reads `render.yaml` and shows one service, `vada`, on the free plan.
4. When prompted for `GEMINI_API_KEY`, paste the key. It is stored as a Render
   secret and never written to the repository.
5. Press **Apply**. The first build takes 5-10 minutes because the image installs
   `chromadb`.

When the build finishes, Render shows a URL of the form
`https://vada-xxxx.onrender.com`.

### Without the blueprint

If you prefer to click through the dashboard:

1. **New** -> **Web Service** -> connect the repository.
2. Language: **Docker**. Dockerfile path: `Dockerfile`.
3. Instance type: **Free**. Region: **Singapore**.
4. Health check path: `/health`.
5. Add environment variables: `GEMINI_API_KEY` (secret),
   `VADA_EMBEDDING_MODEL=gemini-embedding-001`,
   `VADA_LLM_MODEL=gemini-3.1-flash-lite`.
6. **Create Web Service**.

## Verify a deployment

Run these in order; each one proves a different layer.

```powershell
# 1. The process is alive and the app started
#    expect {"status":"ok","service":"vada","version":"1.0.0"}
Invoke-RestMethod https://YOUR-URL.onrender.com/health

# 2. The indexes exist and match the corpus
#    expect "indexed": true, "chunks": 60, "vectors": 60, "stale": false
Invoke-RestMethod https://YOUR-URL.onrender.com/api/index/status

# 3. Retrieval returns cards
$body = @{ query = "Which field replaced user_name in v3?"; limit = 5 } | ConvertTo-Json
Invoke-RestMethod https://YOUR-URL.onrender.com/api/search -Method Post -ContentType "application/json" -Body $body

# 4. Generation works end to end
$body = @{ question = "Which field replaced user_name in v3?"; limit = 5 } | ConvertTo-Json
Invoke-RestMethod https://YOUR-URL.onrender.com/api/ask -Method Post -ContentType "application/json" -Body $body
```

In the browser, check three things:

1. the page loads and the header shows the theme toggle,
2. the first question returns an answer with citations and a confidence row,
3. an unrelated question ("How do I bake sourdough bread?") returns
   **not found** with zero cards.

If step 1 returns `"chunks": 0` or `"indexed": false`, the boot-time index build
did not run. See troubleshooting.

## What the free plan means

| Behaviour | Consequence | What to do |
| --- | --- | --- |
| Sleeps after ~15 minutes idle | The next request waits 30-60 s while the container starts and the index rebuilds. | Open the URL once before you show it to anyone. |
| Ephemeral disk | Every deploy and restart starts with a fresh index; feedback is per-instance. | Nothing to fix. The index is rebuilt from `corpus/` at boot. |
| 512 MB RAM | Enough for 60 chunks, but not for a large corpus. | Fine for the sample corpus; a real corpus needs a paid instance. |
| Shared CPU | First answers take 5-10 s, cached answers under 100 ms. | Ask the demo questions once to warm the cache. |

Cold starts are the reason the viva demo runs on the local server: the deployed
URL is evidence that the product runs in the cloud, not the demo surface itself.

## Updating the deployed app

Push to `main`. Render rebuilds and redeploys automatically.

- Editing `corpus/*.md` does not need a special step: the image builds the index
  at boot, so the new deploy picks the changes up.
- Editing `app/**` redeploys the same way.
- To force a rebuild without a code change, use **Manual Deploy** ->
  **Clear build cache & deploy** in the Render dashboard.

## Environment variables

| Variable | Purpose | Default |
| --- | --- | --- |
| `GEMINI_API_KEY` | Embeddings and answer generation. Without it the app runs keyword-only and quotes passages verbatim. | unset |
| `VADA_EMBEDDING_MODEL` | Embedding model. | `gemini-embedding-001` |
| `VADA_LLM_MODEL` | Generation model. | `gemini-3.1-flash-lite` |
| `PORT` | Injected by Render; the container binds it. | `8000` |

Never commit `.env`. Locally the app reads it; in the cloud Render injects the
same values.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Build fails at `pip install chromadb` | No wheel for the image's Python version | The image pins `python:3.11-slim`; keep it there unless wheels are confirmed. |
| Service starts, then restarts repeatedly | Out of memory, or the port was not bound | Check the logs for `Killed` or `Address already in use`; confirm the `CMD` binds `${PORT}`. |
| `/health` is fine but `/api/ask` returns `not_found` for everything | Index missing or empty | Check `/api/index/status`; redeploy, or open the URL once so `ensure_ready()` rebuilds. |
| Answers take 30+ seconds every time | Cold start after sleep, or the model is slow | Open the URL first, ask one question, then demo. |
| `403` or `API key not valid` in the logs | Key missing, or the wrong secret name | Re-enter `GEMINI_API_KEY` in the Render dashboard. |
| Feedback disappears after a deploy | Ephemeral disk on the free plan | Expected; a paid plan with a persistent disk is required for durable feedback. |

## Cost and teardown

The free plan costs nothing and needs no card. To take it down, open the service
in Render and choose **Suspend** (keeps the URL and settings) or **Delete**
(removes it). Nothing in the repository depends on the service being live.

## Files involved

| File | Role |
| --- | --- |
| `Dockerfile` | Builds the runtime image and starts the server. |
| `.dockerignore` | Keeps `.venv`, tests, secrets and local indexes out of the image. |
| `render.yaml` | Declares the service, plan, region, health check and env vars. |
| `app/retriever.py` (`ensure_ready`) | Rebuilds a missing index on the first request. |
| `app/refresh.py` | Builds the index at boot; also the CLI for local rebuilds. |
