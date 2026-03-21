from supabase import create_client, Client
from backend.config import get_settings


def get_supabase() -> Client:
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_service_key)


supabase: Client = None


def init_supabase() -> Client:
    global supabase
    supabase = get_supabase()
    return supabase
