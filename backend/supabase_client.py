"""Lazy Supabase client factories (anon for auth, service for data)."""
from functools import lru_cache
from supabase import create_client, Client

from backend import config


@lru_cache(maxsize=1)
def anon_client() -> Client:
    """Client with the anon key — used to validate user access tokens."""
    if not config.SUPABASE_URL or not config.SUPABASE_ANON_KEY:
        raise RuntimeError("Supabase anon settings missing. See .env.example.")
    return create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)


@lru_cache(maxsize=1)
def service_client() -> Client:
    """Admin client with the service_role key — bypasses RLS for backend CRUD."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        raise RuntimeError("Supabase service settings missing. See .env.example.")
    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
