"""One server-side Supabase client; never expose this client/key to React."""
from supabase import create_client, ClientOptions
from .config import settings

supabase_service = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY,
    options=ClientOptions(persist_session=False, auto_refresh_token=False),
)
supabase = supabase_service
