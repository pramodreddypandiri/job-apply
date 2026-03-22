from supabase import create_client, Client
from backend.config import get_settings

_client: Client | None = None


def init_supabase() -> Client:
    global _client
    if _client is None:
        settings = get_settings()
        _client = create_client(settings.supabase_url, settings.supabase_service_key)
    return _client


def get_supabase() -> Client:
    return init_supabase()


class _LazyClient:
    """Proxy that initializes Supabase on first attribute access."""
    def __getattr__(self, name):
        return getattr(init_supabase(), name)


supabase: Client = _LazyClient()  # type: ignore
