# NutriWise AI — Diabetes Diet Assistant: Implementation Report

**Status: Diabetes pivot complete.** NutriWise was repurposed from a general
nutrition tracker into a diabetes diet assistant: profile-driven nutrient goals,
daily fasting-glucose logging, GI-aware food scoring, diabetes assessment,
recommendations, and a full-day meal planner.

> Historical note: the earlier IFCT / college-student milestone is superseded by
> this diabetes build. See `README.md` for current usage.

---

## A. What was built

| Area | Change |
|---|---|
| Dataset | Added `glycemic_index` + `gi_category` to `data/nutriwise_foods.csv` via `scripts/prepare_diabetes_data.py` |
| Schemas | New `UserProfile`, `NutrientGoals`, `GlucoseReading`, `DailyPlan`, `DailyPlanMeal`; GI/rating fields on `FoodItem` and `LLMFoodNutritionEstimate` |
| Goals | `nutrition/goals.py` — Mifflin-St Jeor BMR → TDEE → personalized goals |
| Glucose | `nutrition/glucose.py` — categorize readings, adjust carb budget |
| Scoring | `nutrition/diabetes_score.py` — good/moderate/limit rating |
| Lookup | `nutrition/food_lookup.py` — GI/rating annotation + `get_rated_foods()` |
| Assessment | `nutrition/assessment.py` — intake vs goals + glucose |
| Recommender | `nutrition/recommender.py` — diabetes-aware, dataset-sourced suggestions |
| Planner | `nutrition/meal_planner.py` — carb-budgeted full-day plan |
| Tracker | `nutrition/tracker.py` — persist profile + glucose log |
| LLM | `llm/gemini_client.py` — Gemini client for parsing + off-dataset estimates |
| UX | `main.py` diabetes CLI; `demo.py` offline walkthrough |

---

## A2. Full-stack web application (Supabase cloud + React)

The primary web app is a **full-stack, multi-user site** with per-user authentication and a **cloud database**.

**Stack**
- **Database & Auth: Supabase** (hosted Postgres + Supabase Auth). Chosen for lowest setup overhead: no DB server to install, built-in email/password auth, free tier. Schema in `supabase/schema.sql` (tables `profiles`, `glucose_readings`, `meals`, each with Row Level Security).
- **Backend: FastAPI** (`backend/`) — verifies the Supabase access token on every request (`backend/auth.py`), stores/reads per-user data via the service-role client (`backend/db.py`, `backend/supabase_client.py`), and reuses the existing `nutrition/*` engine for goals, scoring, assessment, recommendations, and the planner. Also serves the built frontend (one-command run).
- **Frontend: React 18 + Vite + React Router + Tailwind** (`frontend/`), using `@supabase/supabase-js` for auth. Real multi-page SPA: Login/Register, Dashboard, Log Meal, Glucose, Meal Plan, Profile, with a sidebar layout, protected routes, toasts, and loading/empty states. Built to `frontend/dist` and served by FastAPI.
- **Config bootstrap:** the frontend fetches the public Supabase URL + anon key from `GET /api/config`, so the user configures secrets in **one place** (the backend `.env`) and never needs to rebuild when keys change.

**Per-user data model (Supabase):** `profiles` (one row/user), `glucose_readings` (one row/user/day), `meals` (many rows/user/day). All keyed by `auth.users.id`; RLS restricts rows to their owner.

**Dependencies installed in `conda_env`:** `supabase` 2.18.1, `pyjwt` 2.10.1, `python-dotenv` 1.0.1 (FastAPI/uvicorn were already present). Frontend packages install into `frontend/node_modules` via `npm install`.

**What the user sets up (minimal, one-time):**
1. Create a free Supabase project.
2. Copy `.env.example` → `.env` and paste `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_KEY`.
3. Run `supabase/schema.sql` in the Supabase SQL editor.
4. `python -m backend.seed_demo` to create the demo login.

**Run (one command):**
```powershell
conda activate conda_env
cd frontend && npm install && npm run build && cd ..
uvicorn backend.main:app --port 8000      # http://localhost:8000
```

> **Storage note:** per-user data now lives in **Supabase (cloud Postgres)**, not local files. The only secret that must stay server-side is `SUPABASE_SERVICE_KEY` (kept in `.env`, never shipped to the browser). The app targets localhost but, unlike the earlier prototype, has real auth and a cloud DB, so it is closer to deployable (would still want HTTPS, rate limiting, and email-confirmation review before public hosting).

### A3. Earlier local-only prototype (retained)

### A3. Codebase cleanup

The pre-web prototype has been removed to keep the codebase focused on the
website: the old CDN-React app (`web/`), the terminal CLI/demo (`main.py`,
`demo.py`, `meal_processor.py`, `nutrition/tracker.py`), and the legacy IFCT data
and scripts are deleted. Files are organized into `backend/`, `frontend/`,
`nutrition/`, `models/`, `llm/`, `scripts/` (dataset prep), `supabase/` (SQL), and
`docs/`. The Supabase full-stack app under `backend/` + `frontend/` is the product.

---

## A4. Round 3 additions (time, activity, history, analysis)

**Time component.** Meals, glucose, and activities now carry the user's local
time. Logging asks for the time eaten; the app sends local date + time so
"today" and timestamps follow the user's clock, not the server's. Times show on
the dashboard and history, the meal planner suggests eating windows per slot, and
the Recommendations page lists best-time guidance.

**Meals — one per type/day with replace/merge + audit (per the chosen model).**
Each day holds a single row per meal type (unique constraint). Logging a type
that already exists prompts **Add to it** (merge) or **Replace** (correction).
Every create / merge / replace / delete is written to a `meal_audit` table
(immutable trail with a before-snapshot), so corrections are possible but fully
traceable — the "allow edits but keep history, single entry per day" model.

**More nutrients.** Added approximate micronutrient columns to the dataset
(`vitamin_a/c/d/b12`, `folate`, `magnesium`, `zinc` via `scripts/prepare_micros.py`),
flowed them through the `Nutrition` model and calculator, and show a
**Micronutrients** panel (10 nutrients vs reference targets). Clearly labeled as
estimates — no fabricated precision.

**Activity tracker.** New `activities` table + MET-based calorie estimation
(`nutrition/activity.py`). Logged exercise raises that day's calorie **and** carb
budget, feeding assessment, recommendations, and the planner.

**New pages / endpoints.**
- **Recommendations** page — next-meal priorities, best-time windows + timing
  tips, a **food-exchange** explorer ("instead of X eat Y"), and an **"is this OK
  to eat?"** checker (`/api/meal-check`, `/api/exchanges`).
- **History** page — every logged day since joining (`/api/history`).
- **Analysis** page — rules-based weekly/all-time stats, insights, and a
  next-week plan, with an **optional Gemini narrative**
  (`/api/analysis`, `nutrition/analysis.py`).

**Schema migration:** `supabase/migration_2.sql` (meal time/updated_at + unique
constraint, `meal_audit`, `activities`). Read paths degrade gracefully before it
is applied; write paths return a clear "run migration" message.

**LLM fallback for guidance.** Food exchange and the "is this OK?" checker now
fall back to Gemini when a food isn't in the dataset: the exchange tool returns
an AI estimate + swaps (and always offers dataset "good" foods even offline), and
the checker folds LLM-estimated nutrition for off-dataset items into its verdict.

**Saved analyses.** Analyses are now persisted (`supabase/migration_3.sql`,
`analyses` table). The Analysis page shows previous analyses first and never
auto-runs; the user triggers **this week / all time / custom range** on demand.

---



Fasting blood glucose in **mg/dL**, logged once per day:

- **< 100** → normal (carb budget ×1.0)
- **100–125** → elevated (×0.9, low-GI emphasis)
- **≥ 126** → high (×0.8, strong low-GI + low-sugar steer)

Optional post-meal readings use 140 / 180 mg/dL thresholds.

---

## C. Personalized goals (example)

Profile: 54 y male, 84 kg / 170 cm (BMI 29.1), light activity, Type 2, hypertension.

```
Calories:      2026 kcal   (trimmed ~10% for weight management)
Carb budget:   228 g
Sugar ceiling: 25 g
Fiber minimum: 28 g
Protein:       101 g
Fat:           79 g
Sodium ceiling:1500 mg      (tightened for hypertension)
```

A high fasting reading (142 mg/dL) that day reduces the carb budget to **182 g**.

---

## D. GI dataset

```
150 foods | GI breakdown: low (<=55): 63, medium (56-69): 66, high (>=70): 21
```

GI values are approximate educational estimates (see `scripts/prepare_diabetes_data.py`),
not clinically validated. Food ratings combine GI with per-serving sugar, fiber,
and carbohydrate load.

---

## E. Tests

Deterministic suite:

```
tests/test_calculator.py        5
tests/test_food_lookup.py        9
tests/test_tracker.py           10  (+ profile/glucose persistence)
tests/test_llm_fallback.py       5  (mocked)
tests/test_diabetes.py          18  (goals, glucose, scoring, planner, annotation)
test_integration.py              5  (diabetes end-to-end)
--------------------------------------------
Total                           52 passed
```

Run:

```powershell
python -m pytest -q tests/test_calculator.py tests/test_food_lookup.py \
  tests/test_tracker.py tests/test_llm_fallback.py tests/test_diabetes.py test_integration.py
```

The LLM (Gemini) is used only for off-dataset foods and the analysis summary.

---

## F. Design principles kept

- **Deterministic math** — all nutrition/goal calculations are Python, verifiable.
- **Explainable** — every food tagged with source + GI + rating; every assessment
  states the number vs the goal.
- **No hallucinated data** — dataset is primary; LLM only parses language or
  estimates genuinely missing foods (clearly labeled).
- **Diet-only safety boundary** — no insulin dosing or medical treatment advice.

---

## G. Known limitations

1. GI values and goal formulas are approximate, not clinically validated.
2. JSON storage; single-user prototype.
3. Off-dataset foods and the AI summary depend on a configured Gemini API key.
4. The planner caps carbohydrates but not protein, so generated plans can exceed
   the protein target.

---

## H. Disclaimer

NutriWise is an educational prototype, **not** a medical device. It does not
diagnose, treat, or dose medication, and gives no insulin guidance. Users with
diabetes must consult their healthcare team for treatment decisions.
