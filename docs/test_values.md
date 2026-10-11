# NutriWise — End-to-End Test Values

Use these to click through the whole site and confirm each piece works. Start the
app, open **http://localhost:8000**.

```powershell
conda activate conda_env
uvicorn backend.main:app --port 8000
```

All food GI/ratings and goal numbers below are the actual values the app produces,
so you can check the screen against them.

---

## 0. Quick path — demo account

On the login screen click **“Try the demo account”** (or sign in with):

| Field | Value |
|---|---|
| Email | `demo@nutriwise.app` |
| Password | `nutriwise123` |

The demo user already has a profile, a glucose reading, and one meal, so the
Dashboard is populated immediately.

---

## 1. Register a fresh account (tests auth + empty state)

On the login screen choose **Register**:

| Field | Value |
|---|---|
| Email | `ravi.test@example.com` |
| Password | `test1234` |

**Expect:** you’re signed in and redirected to **Profile** with a banner saying to
finish setup (a brand-new account has no profile yet).
*(If Supabase “Confirm email” is ON, you’ll be asked to confirm by email first —
use the demo account instead, or turn that off in Supabase → Authentication → Email.)*

---

## 2. Create the profile (tests goal calculation)

On the **Profile** page enter:

| Field | Value |
|---|---|
| Name | `Ravi` |
| Age | `50` |
| Gender | `male` |
| Weight (kg) | `85` |
| Height (cm) | `175` |
| Activity | `light` |
| Diabetes type | `type2` |
| On insulin | unchecked |
| HbA1c | `7.6` |
| Conditions | select **hypertension** |

Click **Save profile & recompute goals**.

**Expect — “Your daily goals” panel:**

| Goal | Value |
|---|---|
| Calories | **2102 kcal** |
| Carb budget | **236 g** |
| Sugar ceiling | **25 g** |
| Fiber minimum | **29 g** |
| Protein | **105 g** |
| Fat | **82 g** |
| Sodium ceiling | **1500 mg** (tightened — because of hypertension) |
| BMI | **27.8** |

Notes should mention the ~10% calorie trim (BMI ≥ 25) and the 1500 mg sodium cap.

---

## 3. Log glucose (tests the daily carb-budget adjustment)

Go to **Glucose**. Try these one at a time and watch the color + message, then
check the Dashboard’s “Carbs (budget)” bar target:

| Reading (mg/dL) | Type | Expect category | Carb budget becomes |
|---|---|---|---|
| `92` | fasting | **normal** (green) | 236 g (×1.0) |
| `115` | fasting | **elevated** (amber) | **212 g** (×0.9) |
| `150` | fasting | **high** (red) | **189 g** (×0.8) |

Leave it on **150 (high)** for the next steps so you can see the budget tighten.
Only one reading is kept per day — re-logging overwrites it.

---

## 4. Log meals (tests food search, GI/rating, tracking, assessment)

Go to **Log Meal**. Search each food, **Add**, set quantity/unit, pick the meal
type, then **Log this meal**.

### Meal A — Breakfast (balanced)
| Food | Qty | Unit | Expect chip |
|---|---|---|---|
| `Idli` | 3 | piece | GI 69 · **moderate** |
| `Dal Tadka` | 1 | bowl | GI 30 · **good** |

### Meal B — Lunch (carb/sugar heavy, should trip warnings)
| Food | Qty | Unit | Expect chip |
|---|---|---|---|
| `Steamed White Rice` | 250 | g | GI 73 · **limit** |
| `Chicken Biryani` | 200 | g | GI 60 · **moderate** |
| `Cola` | 1 | glass | GI 63 · **limit** |

**Expect after Meal B (Dashboard):**
- **Carbs (budget)** bar turns **red** (you blow past the 189 g high-glucose budget).
- **Sugar (max)** bar red (Cola pushes sugar over 25 g).
- Assessment lists carbs over budget + sugar over ceiling (+ likely sodium).
- Recommendations show **high-priority** “keep next meal low-GI / out of carb budget”
  with suggested good foods (Dal Tadka, Palak Paneer, Grilled Chicken, etc.).

### Meal C — Dinner (recovery, low-GI)
| Food | Qty | Unit | Expect chip |
|---|---|---|---|
| `Grilled Chicken` | 1 | serving | GI 5 · **good** |
| `Broccoli` | 1 | bowl | GI 15 · **good** |

---

## 5. Filter test (tests the rating filter)

On **Log Meal**, set the rating dropdown to **Good** → only low-GI/high-fiber items
show (dals, curries, grilled proteins, most vegetables). Set to **Limit** → sugary
drinks, white rice, fried/dessert items show.

---

## 6. Natural-language logging (AI)

In **“Or describe your meal”** type:
```
2 idlis and a cup of sambar
```
- **If `GEMINI_API_KEY` is set:** items are parsed into the cart to review, then log.
- **If not:** you get a clean message “AI meal parsing isn't configured.” (expected, not a crash).

A food **not** in the dataset (e.g. `gulab jamun`) won’t appear in search; type it and
use **“Add as a custom food”** — the AI estimates its nutrition so it can be logged.

---

## 7. Meal Plan (tests the planner)

Go to **Meal Plan** → it auto-generates. With the **high (150)** reading still set:
- Four cards: breakfast / lunch / dinner / snack, each with a carb budget.
- Foods are low-GI picks (dals, curries, grilled proteins, vegetables).
- A note says the carb budget was **reduced** for today based on your glucose.
- Click **Regenerate** to rebuild.

---

## 8. Multi-user isolation (tests auth separation)

1. **Sign out** (sidebar).
2. Log in as the **demo** account → you should see the demo’s data, **not** Ravi’s.
3. Log back in as `ravi.test@example.com` → Ravi’s meals/glucose are still there.

Each account only ever sees its own data (enforced server-side).

---

## 9. Reset (optional)

To clear a day’s meals for the logged-in user, the backend exposes
`POST /api/reset-day` (used internally). Logging a new glucose value just
overwrites the day’s reading.

---

### Quick reference — food ratings used above
| Food | GI | Rating |
|---|---|---|
| Grilled Chicken | 5 | good |
| Broccoli | 15 | good |
| Dal Tadka | 30 | good |
| Brown Rice | 55 | good |
| Chicken Biryani | 60 | moderate |
| Idli / Masala Dosa | 69 | moderate |
| Cola | 63 | limit |
| Steamed White Rice | 73 | limit |

---

## Round 3 features (time, activity, history, analysis)

> Requires `supabase/migration_2.sql` to be run in Supabase (see docs/WEB_SETUP.md 3b).

### 10. Meal time + duplicate handling
- **Log Meal** now has a **Time eaten** field (defaults to now). Log *Breakfast* = `Idli ×3` at `08:00`.
- Log *Breakfast* **again** (e.g. `Banana ×1`). Expect a prompt:
  - **Add to it** → merges into the morning breakfast (carbs add up).
  - **Replace** → overwrites it (use for a wrong entry).
- On the **Dashboard**, meals show their time; the ✕ removes a meal. Every change
  is recorded in the audit trail (`GET /api/meal/audit`).

### 11. Activity → budget bump
On the **Activity** page log:
| Field | Value |
|---|---|
| Activity | `brisk walking` |
| Duration | `30` |
| Time | `18:00` |

**Expect:** ~**180–190 kcal** burned, and the Dashboard "Calories/Carbs" targets
rise by that amount (goals note shows "+N kcal for today's activity").

### 12. Recommendations page
- **Best times to eat** lists windows (breakfast 7–9 AM, etc.) + timing tips.
- **Food exchange:** type `Steamed White Rice` → expect it flagged for swap with
  alternatives like **Brown Rice, Chapati, Dal Rice**. Type `Cola` → swaps like
  **Buttermilk, Black Coffee**.
- **"Is this OK to eat?":** add `Cola` + `French Fries` → expect verdict
  **Think twice** with reasons (carbs/sugar) and swap suggestions.

### 13. Micronutrients
On the **Dashboard**, the **Micronutrients today** panel shows calcium, iron,
magnesium, zinc, potassium, and vitamins A/C/D/B12/folate vs reference targets.
Log an `Orange` and watch **Vitamin C** jump. (Values are labeled estimates.)

### 14. History & Analysis
- **History** lists every day you've logged, with meals (+times), glucose badge,
  and activity minutes.
- **Analysis** (This week / All time) shows avg fasting glucose, days in range,
  avg carbs/fiber/sugar, days over budget, activity total, insights, and a
  **next-week plan**, plus a clean built-in coach summary (and an optional AI rewrite)
  appears on top.

### 15. Timezone check
Log a meal late at night — it should attach to the correct local calendar day
(not jump to the next/previous day), because the app uses your local date.

---

## Round 4 tweaks (LLM food guidance + saved analyses)

> Saved analyses need `supabase/migration_3.sql` (docs/WEB_SETUP.md 3b).

### 16. Food exchange / meal-check beyond the dataset
On the **Recommendations** page, in **Food exchange**, type a food that isn't in
the dataset, e.g. `Gulab Jamun` or `Pani Puri`:
- **Gemini configured:** you get an AI estimate (GI + an "AI estimate" badge) and tailored swaps.
- **No key:** you still get solid dataset low-GI options + a short note (never a dead "not in dataset" message).

Same for **"Is this OK to eat?"** — add a non-dataset item; with Gemini set, its nutrition is estimated and folded into the verdict (a note says "estimated by AI").

### 17. Analysis page (previous first, run on demand)
Open **Analysis**:
- It **does not auto-run** — it shows your **previous saved analyses** first
  (empty on first visit).
- Click **New: this week** or **New: all time**, or **Custom range** → pick two
  dates → **Run analysis**. The result is saved and appears at the top under
  "Latest", then persists under "Previous analyses" (each can be deleted).
