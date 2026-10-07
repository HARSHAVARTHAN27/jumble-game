import os
from pathlib import Path
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)

def env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name, str(default)).strip().lower()
    if value in ("true", "1", "yes", "on"):
        return True
    if value in ("false", "0", "no", "off"):
        return False
    raise ValueError(f"{name} must be true or false.")


def player_cookie_samesite(environment: str) -> str:
    # Render and Vercel use different sites. Production cookies must permit
    # those requests unless a same-site deployment explicitly opts into lax.
    value = os.getenv('PLAYER_COOKIE_SAMESITE', 'lax' if environment == 'development' else 'none').strip().lower()
    if value not in ('lax', 'strict', 'none'):
        raise ValueError('PLAYER_COOKIE_SAMESITE must be lax, strict or none.')
    if value == 'none' and environment == 'development':
        raise ValueError('PLAYER_COOKIE_SAMESITE=none requires ENVIRONMENT=production for secure cookies.')
    return value

class Settings:
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_ANON_KEY: str = (
        os.getenv("SUPABASE_ANON_KEY") or os.getenv("SUPABASE_PUBLISHABLE_KEY", "")
    )
    SUPABASE_SERVICE_ROLE_KEY: str = (
        os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_SECRET_KEY", "")
    )
    FRONTEND_URL: str = os.getenv("FRONTEND_URL", "http://localhost:5173").rstrip('/')
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    AUTO_MIGRATE: bool = env_bool("AUTO_MIGRATE", True)
    PLAYER_COOKIE_SAMESITE: str = player_cookie_samesite(ENVIRONMENT)

settings = Settings()
