from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from postgrest.exceptions import APIError
from contextlib import asynccontextmanager, suppress
import asyncio
from .routers.live import host_router as live_host_router, player_router as live_player_router, socket_router, deadline_worker
from .routers.game import router as game_router
from .routers.host import router as host_router
from .routers.employee import router as employee_router
from .config import settings
from .database import supabase
from .exceptions import AppError
from .services.game_service import GameService
from .migrations import run_migrations


@asynccontextmanager
async def lifespan(application):
    await startup()
    task = asyncio.create_task(deadline_worker())
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task


app = FastAPI(
    title="Jumble Backend",
    description="Backend for real-time multiplayer team game",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration
allowed_origins = [settings.FRONTEND_URL]
if settings.ENVIRONMENT == "development":
    allowed_origins.append("http://localhost:5173")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
@app.exception_handler(AppError)
@app.exception_handler(APIError)
async def global_exception_handler(request, exc):
    from .exceptions import AppError
    # Check if it's our custom AppError
    if isinstance(exc, AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                },
            },
        )
    if isinstance(exc, APIError) and str(exc.code) in ('PGRST205', 'PGRST202'):
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "DATABASE_NOT_INITIALIZED",
                    "message": "Database setup is incomplete. Configure DATABASE_URL and restart the backend with AUTO_MIGRATE=true. For manual setup, see backend/README.md.",
                },
            },
        )
    # Generic error: do not send database details or stack traces to players.
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "data": None,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "The game server encountered an unexpected error.",
            },
        },
    )


# Health endpoint
@app.get("/health")
async def health_check():
    return {"status": "healthy", "environment": settings.ENVIRONMENT,
            "database": getattr(app.state, "database_status", "unchecked")}


# Register routers
app.include_router(game_router)
app.include_router(host_router)
app.include_router(live_host_router)
app.include_router(live_player_router)
app.include_router(socket_router)
app.include_router(employee_router)


# Supabase on startup event
async def startup():
    if settings.AUTO_MIGRATE:
        # Deliberately outside the health-check exception handler: never serve a
        # partially migrated release or start its timer worker after a failure.
        applied = await asyncio.to_thread(run_migrations, settings.DATABASE_URL)
        print(f"Database migrations applied: {', '.join(applied)}" if applied else 'Database migrations are up to date.')
    # A missing schema and an empty lobby are different from a connection failure.
    try:
        for table in ('games', 'teams', 'employees', 'players'):
            supabase.from_(table).select('id').limit(1).execute()
        app.state.database_status = 'ready'
        print('Supabase connection successful')
        try:
            GameService(supabase).get_active_game()
        except Exception as exc:
            if isinstance(exc, AppError) and exc.code == 'NO_ACTIVE_GAME':
                print('No active game; waiting for a host to create a lobby.')
            else:
                raise
    except APIError as exc:
        app.state.database_status = 'schema_missing' if str(exc.code) == 'PGRST205' else 'connection_failed'
        if app.state.database_status == 'schema_missing':
            print('Supabase reachable, but foundation schema is missing. Configure automatic migrations or follow the manual setup in backend/README.md.')
        else:
            print('Supabase database/auth check failed. Check backend environment and permissions.')
    except Exception:
        app.state.database_status = 'connection_failed'
        print('Supabase connection failed. Check network and backend environment.')
