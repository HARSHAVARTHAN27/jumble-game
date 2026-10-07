"""One server-side Supabase client; never expose this client/key to React."""
from supabase import create_client, ClientOptions
from .config import settings
from .database_http import create_database_http_client

supabase_http_client = create_database_http_client()

supabase_service = create_client(
    settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE_KEY,
    options=ClientOptions(persist_session=False, auto_refresh_token=False,
                          httpx_client=supabase_http_client),
)
supabase = supabase_service
