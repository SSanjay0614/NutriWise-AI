# Deploying NutriWise

The app is one FastAPI service that **also serves the built React frontend**, talks
to **Supabase** (cloud Postgres + auth) and **Google Gemini**. Because the backend
is Python + pandas, the simplest reliable host is a container platform like
**Render** (free tier) using the included `Dockerfile`.

> **About Vercel:** Vercel is excellent for the React frontend, but it runs the
> backend as Python *serverless functions*, which is awkward for a pandas app with
> data files. The cleanest path is to host the **whole app as one container** (below).
> If you specifically want Vercel, see "Option B" at the bottom.

---

## What's already done
- ✅ **Supabase**: database + auth (you ran `supabase/schema.sql`, `migration_2.sql`, `migration_3.sql`).
- ✅ **Gemini**: you have a `GEMINI_API_KEY` + `GEMINI_MODEL`.

## What's left
1. Push the code to GitHub.
2. Create one web service on Render from the repo (it uses the `Dockerfile`).
3. Set the environment variables.
4. Open the URL.

---

## Step 1 — Push to GitHub
Create an **empty** repo on github.com (no README). Then, in the project folder:

```bash
git init
git add .
git commit -m "NutriWise diabetes diet assistant"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

`.gitignore` already excludes `.env`, `node_modules`, `dist`, and caches — your
secrets are **not** pushed.

## Step 2 — Deploy on Render (recommended)
1. Go to <https://render.com> → sign up (free) → **New +** → **Web Service**.
2. Connect your GitHub and pick the repo.
3. Render detects the **Dockerfile** automatically. Leave build/start commands blank
   (the Dockerfile handles them). Instance type: **Free**.
4. Click **Advanced → Add Environment Variable** and add each of these
   (from your local `.env`):

   | Key | Value |
   |---|---|
   | `SUPABASE_URL` | your project URL |
   | `SUPABASE_ANON_KEY` | anon public key |
   | `SUPABASE_SERVICE_KEY` | service_role key |
   | `GEMINI_API_KEY` | your Gemini key |
   | `GEMINI_MODEL` | `gemini-2.0-flash` (or your choice) |
   | `DEMO_EMAIL` | `demo@nutriwise.app` |
   | `DEMO_PASSWORD` | `nutriwise123` |

   (Don't set `PORT` — Render provides it.)
5. **Create Web Service**. First build takes a few minutes (installs deps, builds the
   frontend). When it's live you get a URL like `https://nutriwise.onrender.com`.

> Free Render services sleep after ~15 min idle, so the first request after a nap
> takes ~30–60s to wake. Fine for a demo; upgrade later if you want it always-on.
> **Railway** (<https://railway.app>) is a good alternative with the same Dockerfile.

## Step 3 — Seed the demo account (optional, once)
Render → your service → **Shell**, then:
```bash
python -m backend.seed_demo
```
Or just register a normal account on the site.

## Step 4 — Supabase auth settings
In Supabase → **Authentication → URL Configuration**, add your deployed URL to
**Site URL** / redirect allow-list. If you'd rather skip email confirmation, turn it
off under **Authentication → Providers → Email** (the demo account is always confirmed).

---

## Updating later
Push to GitHub and the host redeploys automatically:
```bash
git add .
git commit -m "describe your change"
git push
```

---

## Option B — Vercel (frontend) + Render (backend)
Only if you want the frontend on Vercel specifically:
1. Deploy the backend on Render as above → note its URL.
2. In Vercel, import the repo, set **Root Directory** to `frontend`, framework **Vite**
   (build `npm run build`, output `dist`).
3. The frontend calls `/api/...` relative, so add a `vercel.json` rewrite sending
   `/api/*` to your Render backend, and allow the Vercel domain in the backend's CORS.
   (Ask and I'll wire this up — it's a bit more config than Option A.)

For a single beginner-friendly deploy, **Option A (Render, one service)** is the way.
