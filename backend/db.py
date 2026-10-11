"""Per-user data access against Supabase tables (service-role, scoped by user_id)."""
from typing import Optional, List
from backend.supabase_client import service_client


# ------------------------------------------------------------------ profiles
def get_profile(user_id: str) -> Optional[dict]:
    res = service_client().table("profiles").select("*").eq("user_id", user_id).limit(1).execute()
    return res.data[0] if res.data else None


def upsert_profile(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    res = service_client().table("profiles").upsert(payload, on_conflict="user_id").execute()
    return res.data[0] if res.data else payload


# ------------------------------------------------------------- glucose readings
def get_glucose(user_id: str, reading_date: str) -> Optional[dict]:
    res = (service_client().table("glucose_readings").select("*")
           .eq("user_id", user_id).eq("reading_date", reading_date).limit(1).execute())
    return res.data[0] if res.data else None


def upsert_glucose(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    res = (service_client().table("glucose_readings")
           .upsert(payload, on_conflict="user_id,reading_date").execute())
    return res.data[0] if res.data else payload


def all_glucose(user_id: str) -> List[dict]:
    res = (service_client().table("glucose_readings").select("*")
           .eq("user_id", user_id).order("reading_date").execute())
    return res.data or []


# ------------------------------------------------------------------- meals
def list_meals(user_id: str, meal_date: str) -> List[dict]:
    res = (service_client().table("meals").select("*")
           .eq("user_id", user_id).eq("meal_date", meal_date)
           .order("created_at").execute())
    return res.data or []


def get_meal(user_id: str, meal_date: str, meal_type: str) -> Optional[dict]:
    res = (service_client().table("meals").select("*")
           .eq("user_id", user_id).eq("meal_date", meal_date)
           .eq("meal_type", meal_type).limit(1).execute())
    return res.data[0] if res.data else None


def upsert_meal(user_id: str, data: dict) -> dict:
    """Insert or replace the single row for (user, meal_date, meal_type)."""
    payload = {**data, "user_id": user_id}
    res = (service_client().table("meals")
           .upsert(payload, on_conflict="user_id,meal_date,meal_type").execute())
    return res.data[0] if res.data else payload


def delete_meal(user_id: str, meal_date: str, meal_type: str) -> None:
    (service_client().table("meals").delete()
     .eq("user_id", user_id).eq("meal_date", meal_date).eq("meal_type", meal_type).execute())


def delete_meals_for_day(user_id: str, meal_date: str) -> None:
    (service_client().table("meals").delete()
     .eq("user_id", user_id).eq("meal_date", meal_date).execute())


def all_meals(user_id: str) -> List[dict]:
    res = (service_client().table("meals").select("*")
           .eq("user_id", user_id).order("meal_date").execute())
    return res.data or []


# ------------------------------------------------------------------- audit
def add_audit(user_id: str, meal_date: str, meal_type: str, action: str, snapshot: dict) -> None:
    # Best-effort: never block a meal write if the audit table isn't present yet.
    try:
        service_client().table("meal_audit").insert({
            "user_id": user_id, "meal_date": meal_date, "meal_type": meal_type,
            "action": action, "snapshot": snapshot or {},
        }).execute()
    except Exception:
        pass


def meal_audit(user_id: str, meal_date: Optional[str] = None, limit: int = 50) -> List[dict]:
    try:
        q = service_client().table("meal_audit").select("*").eq("user_id", user_id)
        if meal_date:
            q = q.eq("meal_date", meal_date)
        res = q.order("created_at", desc=True).limit(limit).execute()
        return res.data or []
    except Exception:
        return []


# ------------------------------------------------------------------ activities
def list_activities(user_id: str, activity_date: str) -> List[dict]:
    try:
        res = (service_client().table("activities").select("*")
               .eq("user_id", user_id).eq("activity_date", activity_date)
               .order("created_at").execute())
        return res.data or []
    except Exception:
        return []


def add_activity(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    res = service_client().table("activities").insert(payload).execute()
    return res.data[0] if res.data else payload


def delete_activity(user_id: str, activity_id: int) -> None:
    (service_client().table("activities").delete()
     .eq("user_id", user_id).eq("id", activity_id).execute())


def all_activities(user_id: str) -> List[dict]:
    try:
        res = (service_client().table("activities").select("*")
               .eq("user_id", user_id).order("activity_date").execute())
        return res.data or []
    except Exception:
        return []


# ------------------------------------------------------------------ analyses
def add_analysis(user_id: str, data: dict) -> dict:
    payload = {**data, "user_id": user_id}
    res = service_client().table("analyses").insert(payload).execute()
    return res.data[0] if res.data else payload


def list_analyses(user_id: str, limit: int = 30) -> List[dict]:
    try:
        res = (service_client().table("analyses").select("*")
               .eq("user_id", user_id).order("created_at", desc=True).limit(limit).execute())
        return res.data or []
    except Exception:
        return []


def delete_analysis(user_id: str, analysis_id: int) -> None:
    (service_client().table("analyses").delete()
     .eq("user_id", user_id).eq("id", analysis_id).execute())


def update_analysis(user_id: str, analysis_id: int, data: dict) -> None:
    (service_client().table("analyses").update(data)
     .eq("user_id", user_id).eq("id", analysis_id).execute())
