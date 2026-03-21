"""Typed query helpers for Supabase tables."""

from backend.db.client import supabase


# ── Users Profile ──────────────────────────────────────────────

def get_user_profile(user_id: str) -> dict | None:
    result = supabase.table("users_profile").select("*").eq("id", user_id).maybe_single().execute()
    return result.data


def upsert_user_profile(user_id: str, data: dict) -> dict:
    result = supabase.table("users_profile").upsert({"id": user_id, **data}).execute()
    return result.data[0]


# ── Skill Graph ────────────────────────────────────────────────

def get_skill_graph(user_id: str) -> list[dict]:
    result = supabase.table("skill_graph").select("*").eq("user_id", user_id).execute()
    return result.data


def upsert_skill(user_id: str, skill_name: str, data: dict) -> dict:
    result = supabase.table("skill_graph").upsert(
        {"user_id": user_id, "skill_name": skill_name, **data}
    ).execute()
    return result.data[0]


# ── Applications ───────────────────────────────────────────────

def create_application(data: dict) -> dict:
    result = supabase.table("applications").insert(data).execute()
    return result.data[0]


def get_application(application_id: str) -> dict | None:
    result = supabase.table("applications").select("*").eq("id", application_id).maybe_single().execute()
    return result.data


def get_user_applications(user_id: str, status: str | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    query = supabase.table("applications").select("*", count="exact").eq("user_id", user_id)
    if status:
        query = query.eq("status", status)
    result = query.order("created_at", desc=True).range(offset, offset + limit - 1).execute()
    return result.data


def update_application(application_id: str, data: dict) -> dict:
    result = supabase.table("applications").update(data).eq("id", application_id).execute()
    return result.data[0]


def find_application_by_url(user_id: str, canonical_url: str) -> dict | None:
    result = (
        supabase.table("applications")
        .select("*")
        .eq("user_id", user_id)
        .eq("canonical_url", canonical_url)
        .maybe_single()
        .execute()
    )
    return result.data


def find_application_by_fingerprint(user_id: str, fingerprint: str) -> dict | None:
    result = (
        supabase.table("applications")
        .select("*")
        .eq("user_id", user_id)
        .eq("role_fingerprint", fingerprint)
        .maybe_single()
        .execute()
    )
    return result.data


# ── Resumes ────────────────────────────────────────────────────

def create_resume(data: dict) -> dict:
    result = supabase.table("resumes").insert(data).execute()
    return result.data[0]


def get_resume_by_application(application_id: str) -> dict | None:
    result = (
        supabase.table("resumes")
        .select("*")
        .eq("application_id", application_id)
        .maybe_single()
        .execute()
    )
    return result.data


def update_resume(resume_id: str, data: dict) -> dict:
    result = supabase.table("resumes").update(data).eq("id", resume_id).execute()
    return result.data[0]


# ── Tracker Events ─────────────────────────────────────────────

def create_tracker_event(data: dict) -> dict:
    result = supabase.table("tracker_events").insert(data).execute()
    return result.data[0]


def get_application_events(application_id: str) -> list[dict]:
    result = (
        supabase.table("tracker_events")
        .select("*")
        .eq("application_id", application_id)
        .order("created_at", desc=True)
        .execute()
    )
    return result.data


# ── Interview Prep ─────────────────────────────────────────────

def get_interview_prep(application_id: str) -> dict | None:
    result = (
        supabase.table("interview_prep")
        .select("*")
        .eq("application_id", application_id)
        .maybe_single()
        .execute()
    )
    return result.data


def create_interview_prep(data: dict) -> dict:
    result = supabase.table("interview_prep").insert(data).execute()
    return result.data[0]


# ── Prep Sessions ──────────────────────────────────────────────

def get_prep_session(user_id: str, session_date: str) -> dict | None:
    result = (
        supabase.table("prep_sessions")
        .select("*, prep_items(*)")
        .eq("user_id", user_id)
        .eq("session_date", session_date)
        .maybe_single()
        .execute()
    )
    return result.data


def create_prep_session(data: dict) -> dict:
    result = supabase.table("prep_sessions").insert(data).execute()
    return result.data[0]


# ── Prep Items ─────────────────────────────────────────────────

def create_prep_items(items: list[dict]) -> list[dict]:
    result = supabase.table("prep_items").insert(items).execute()
    return result.data


def update_prep_item(item_id: str, data: dict) -> dict:
    result = supabase.table("prep_items").update(data).eq("id", item_id).execute()
    return result.data[0]


def get_due_prep_items(user_id: str, date: str, limit: int = 5) -> list[dict]:
    result = (
        supabase.table("prep_items")
        .select("*")
        .eq("user_id", user_id)
        .lte("next_review", date)
        .order("next_review")
        .limit(limit)
        .execute()
    )
    return result.data
