"""Main FastAPI application for Web Notes API.

This module initializes and configures the FastAPI application with all
necessary routers, middleware, and startup/shutdown events.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime
from typing import AsyncGenerator, Dict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse

# Load environment variables from file specified by ENV_FILE (fallback to ".env")
load_dotenv(os.getenv("ENV_FILE", ".env"))

# Import settings after loading env so pydantic's BaseSettings picks up values
from .config import settings  # noqa: E402
from .database import create_tables  # noqa: E402
from .llm.provider_manager import provider_manager  # noqa: E402
from .middleware import (  # noqa: E402
    RequestLoggingMiddleware,
    SecurityHeadersMiddleware,
)
from .routers import (  # noqa: E402
    artifacts,
    llm_providers,
    notes,
    pages,
    sharing,
    sites,
    users,
    web,
)
from .schemas import HealthCheckResponse  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Handle application startup and shutdown.

    This function manages the lifecycle of the application,
    including database initialization and LLM provider loading.
    """
    # Startup
    print("Starting Web Notes API...")

    try:
        # Initialize database tables
        await create_tables()
        print("Database initialized")

        # Load LLM providers from database
        from .database import async_session_maker

        async with async_session_maker() as session:
            await provider_manager.load_providers_from_db(session)
            providers = provider_manager.list_providers()
            print(
                f"Loaded {len(providers)} LLM providers: {', '.join(providers) if providers else 'none'}"
            )

    except Exception as e:
        print(f"Startup failed: {e}")
        raise

    print("Web Notes API started successfully!")

    yield

    # Shutdown
    print("Shutting down Web Notes API...")

    try:
        # Clear LLM providers
        provider_manager.clear_providers()
        print("LLM providers cleared")

        # Close database connections
        # Database connections will be closed automatically
        print("Database connections closed")

    except Exception as e:
        print(f"Shutdown error: {e}")

    print("Web Notes API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title="Web Notes API",
    description="Backend API for Chrome extension web notes app with LLM-powered artifacts",
    version="0.2.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan,
)

# Configure middleware
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware, log_body=False)

# Configure CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",  # Allow all origins for Chrome extension compatibility
    ],
    allow_credentials=False,  # Must be False when allow_origins is "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(users.router)
app.include_router(sites.router)
app.include_router(pages.router)
app.include_router(notes.router)
app.include_router(artifacts.router)
app.include_router(llm_providers.router)
app.include_router(sharing.router)

# Include web dashboard router
app.include_router(web.router)

# Static files for web interface (if needed)
# app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=RedirectResponse)
async def root() -> RedirectResponse:
    """Root endpoint redirecting to dashboard."""
    return RedirectResponse(url="/app/dashboard", status_code=302)


@app.get("/api", response_model=dict)
async def api_root() -> Dict[str, str]:
    """API root endpoint with basic information."""
    return {
        "message": "Web Notes API",
        "version": "0.2.0",
        "docs": "/api/docs",
        "dashboard": "/app/dashboard",
    }


@app.get("/api/health", response_model=HealthCheckResponse)
async def health_check() -> HealthCheckResponse:
    """Comprehensive health check endpoint.

    This endpoint checks the status of the API, database connection,
    and loaded LLM providers.
    """
    try:
        # Test database connection
        from .database import async_session_maker

        async with async_session_maker() as session:
            # Simple query to test connection
            await session.execute("SELECT 1")
            database_connected = True
    except Exception:
        database_connected = False

    # Get provider status
    providers = provider_manager.list_providers()
    provider_status = (
        f"{len(providers)} providers loaded" if providers else "No providers loaded"
    )

    status = "healthy" if database_connected else "degraded"
    message = f"API operational, database {'connected' if database_connected else 'disconnected'}, {provider_status}"

    return HealthCheckResponse(
        status=status,
        message=message,
        timestamp=datetime.utcnow(),
        database_connected=database_connected,
    )


@app.get("/api/status", response_model=dict)
async def detailed_status() -> dict:
    """Detailed status endpoint with comprehensive system information."""
    try:
        # Database status
        from .database import async_session_maker

        async with async_session_maker() as session:
            await session.execute("SELECT 1")
            database_status = "connected"
    except Exception as e:
        database_status = f"error: {str(e)}"

    # LLM provider status
    providers = provider_manager.list_providers()
    provider_tests = await provider_manager.test_all_providers()

    # System information
    return {
        "api": {
            "status": "operational",
            "version": "0.2.0",
            "timestamp": datetime.utcnow().isoformat(),
        },
        "database": {
            "status": database_status,
            "type": "PostgreSQL",
            "url": (
                os.getenv(
                    "DATABASE_URL",
                    "postgresql+asyncpg://postgres:abcd@localhost:5432/webnotes",
                ).split("@")[1]
                if "@" in os.getenv("DATABASE_URL", "")
                else "localhost:5432/webnotes"
            ),
        },
        "llm_providers": {
            "loaded_count": len(providers),
            "loaded_providers": providers,
            "test_results": provider_tests,
        },
        "features": {
            "artifact_generation": True,
            "page_summarization": True,
            "web_dashboard": True,
            "api_documentation": True,
        },
    }


# Exception handlers
@app.exception_handler(404)
async def not_found_handler(request: Request, exc: HTTPException) -> HTMLResponse:
    """Handle 404 errors for web interface."""
    if request.url.path.startswith("/app/"):
        # For web interface, return HTML 404 page
        from .routers.web import templates

        return templates.TemplateResponse(
            "404.html",
            {"request": request, "message": "Page not found"},
            status_code=404,
        )
    else:
        # For API endpoints, return JSON
        raise HTTPException(status_code=404, detail="Endpoint not found")


if __name__ == "__main__":
    import uvicorn

    print("Starting development server...")
    # Development server configuration (use settings)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=int(settings.PORT),
        reload=bool(settings.DEBUG),
        reload_dirs=["app"],
        log_level="info",
    )
