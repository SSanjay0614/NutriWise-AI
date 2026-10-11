# NutriWise Website — Setup (one-time, ~5 minutes)

The full-stack site uses **Supabase** (free cloud Postgres + authentication). You do
four small things; I've built everything else.

---

## 1. Create a free Supabase project
1. Go to <https://supabase.com> → sign in → **New project**.
2. Pick a name, set a database password (any), choose a region, create it.
3. Wait ~1 minute for it to finish provisioning.

## 2. Copy your keys into `.env`
In Supabase: **Project Settings → API**. You'll see:
- **Project URL**
- **anon public** key
- **service_role** key (click to reveal — keep this secret)

In the project folder, copy `.env.example` to `.env` and fill them in:
```
SUPABASE_URL=https://xxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...        # anon public
SUPABASE_SERVICE_KEY=eyJ...     # service_role
DEMO_EMAIL=demo@nutriwise.app
DEMO_PASSWORD=nutriwise123

# LLM — needed for foods not in the dataset, meal parsing, and the analysis summary
GEMINI_API_KEY=AIza...          # from https://aistudio.google.com/apikey
GEMINI_MODEL=gemini-2.0-flash
```

> **Off-dataset foods (Pepsi, Gulab Jamun, …) need `GEMINI_API_KEY`.** Without it,
> the app can only resolve foods that are in the dataset (off-dataset foods and the
> AI summary need the key). After adding or changing the key, **restart the server**.

## 3. Create the database tables
In Supabase: **SQL Editor → New query** → paste the entire contents of
`supabase/schema.sql` → **Run**. (Creates the `profiles`, `glucose_readings`,
and `meals` tables with per-user security.)

### 3b. Apply the migrations (required for time, activity, history & analysis)
Open **SQL Editor → New query** again and run these in order:
1. `supabase/migration_2.sql` — meal time + one-meal-per-type, audit trail, `activities` table.
2. `supabase/migration_3.sql` — saved `analyses` history.

(The app loads without them, but meal/activity logging and saving analyses will
show a "run the latest migration" message until you do this.)

> Optional: to let people log in immediately after registering without an email
> confirmation step, go to **Authentication → Providers → Email** and turn off
> "Confirm email". (The seeded demo account is always confirmed either way.)

## 4. Build the frontend, seed the demo, and run
```powershell
conda activate conda_env

# backend deps (already installed in conda_env, safe to re-run)
pip install -r requirements.txt

# build the React frontend (one-time, or after frontend changes)
cd frontend
npm install
npm run build
cd ..

# create the demo login account
python -m backend.seed_demo

# start the whole site (frontend + API) on one port
uvicorn backend.main:app --port 8000
```

Open **http://localhost:8000**, then either **register** a new account or click
**Try the demo account**.

---

## Everyday use
Just run:
```powershell
conda activate conda_env
uvicorn backend.main:app --port 8000
```

## Developing the frontend (optional, live reload)
Run the backend and the Vite dev server in two terminals:
```powershell
uvicorn backend.main:app --port 8000        # terminal 1
cd frontend && npm run dev                   # terminal 2 -> http://localhost:5173
```
The dev server proxies `/api` to the backend automatically.

---

## Notes
- Your Supabase keys live only in `.env` (backend). The browser receives just the
  public URL + anon key, fetched at runtime from `/api/config` — so you never
  rebuild the frontend when keys change.
- `.env` and `frontend/node_modules` should not be committed to version control.
- Natural-language meal logging and off-dataset food estimation use the Gemini API
  key; everything else works without it.
