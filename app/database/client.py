from functools import lru_cache
from supabase import create_client, Client
from app.core.config import settings


@lru_cache()
def get_supabase_client() -> Client:
    """Get Supabase client with anonymous key for regular operations."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_key
    )


@lru_cache()
def get_supabase_admin_client() -> Client:
    """Get Supabase client with service role key for admin operations."""
    return create_client(
        supabase_url=settings.supabase_url,
        supabase_key=settings.supabase_service_key
    )


def get_database_client() -> Client:
    """Get the appropriate database client based on context."""
    # For now, use admin client for all operations
    # In production, you might want to use different clients based on operation type
    return get_supabase_admin_client()
