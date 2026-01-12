"""Supabase client singleton."""

from functools import lru_cache
from supabase import create_client, Client

from settings.config import get_settings


@lru_cache
def get_supabase_client() -> Client:
    """
    Get cached Supabase client instance.

    Returns:
        Supabase client configured with URL and key from settings.
    """
    settings = get_settings()
    return create_client(settings.supabase_url, settings.supabase_key)
