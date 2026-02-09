import asyncio
import contextlib
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.middleware import RateLimitMiddleware
from app.api.routes import auth, users, groups, tickets, dashboard, api_keys, sla
from app.config import settings
from app.mcp.server import mcp
from app.mcp.tools import tickets as mcp_tickets  # noqa: F401
from app.mcp.tools import info as mcp_info  # noqa: F401
from app.tasks.sla_checker import check_sla_breaches


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        if settings.jwt_secret == "change-me-in-production":
            logging.warning(
                "JWT_SECRET is set to the default value. "
                "This is insecure — set a strong secret in your .env file."
            )
        await stack.enter_async_context(mcp.session_manager.run())
        sla_task = asyncio.create_task(check_sla_breaches())
        yield
        sla_task.cancel()
        try:
            await sla_task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(title="Accio ServiceMeow", version="0.1.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(RateLimitMiddleware)

    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "ok"}

    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
    app.include_router(groups.router, prefix="/api/v1/groups", tags=["groups"])
    app.include_router(tickets.router, prefix="/api/v1/tickets", tags=["tickets"])
    app.include_router(dashboard.router, prefix="/api/v1/dashboard", tags=["dashboard"])
    app.include_router(api_keys.router, prefix="/api/v1/api-keys", tags=["api-keys"])
    app.include_router(sla.router, prefix="/api/v1/sla-config", tags=["sla-config"])

    from app.mcp.auth import McpAuthMiddleware

    app.mount("/mcp", McpAuthMiddleware(mcp.streamable_http_app()))

    return app


app = create_app()
