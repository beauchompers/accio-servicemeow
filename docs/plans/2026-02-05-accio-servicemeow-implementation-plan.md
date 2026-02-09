# Accio ServiceMeow Backend Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a complete backend for a case management platform with REST API, MCP server, SLA tracking, and webhook system — deployable via Docker Compose.

**Architecture:** FastAPI backend with async SQLAlchemy/PostgreSQL, embedded FastMCP server at `/mcp` using Streamable HTTP, Nginx reverse proxy with auto-generated self-signed TLS. Services layer separates business logic from routes.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x (async), asyncpg, Alembic, MCP SDK (FastMCP), PostgreSQL 16, Docker Compose, pytest + httpx

**Reference:** See `docs/plans/2026-02-05-accio-servicemeow-backend-design.md` for full design details.

**MCP SDK Note:** Use `mcp` package v1.26.0. For mounting on FastAPI, use the lifespan pattern with `stateless_http=True`:
```python
import contextlib
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("ServiceMeow", stateless_http=True, json_response=True)

@contextlib.asynccontextmanager
async def lifespan(app):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        yield

app = FastAPI(lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())
```

---

## Task 1: Project Skeleton — Docker Compose, Dockerfiles, Config Files

**Files:**
- Create: `docker-compose.yml`
- Create: `docker-compose.dev.yml`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `nginx/Dockerfile`
- Create: `nginx/nginx.conf`
- Create: `nginx/entrypoint.sh`
- Create: `backend/Dockerfile`
- Create: `backend/entrypoint.sh`
- Create: `backend/pyproject.toml`

**Step 1: Create `.gitignore`**

```gitignore
__pycache__/
*.pyc
.env
*.egg-info/
dist/
.venv/
node_modules/
nginx/certs/
backend/uploads/
.pytest_cache/
*.db
```

**Step 2: Create `.env.example`**

```env
# Database
POSTGRES_USER=servicemeow
POSTGRES_PASSWORD=servicemeow_secret
POSTGRES_DB=servicemeow
DATABASE_URL=postgresql+asyncpg://servicemeow:servicemeow_secret@postgres:5432/servicemeow

# Auth
JWT_SECRET=change-me-in-production
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# Default Admin (created on first run)
DEFAULT_ADMIN_USERNAME=admin
DEFAULT_ADMIN_PASSWORD=admin
DEFAULT_ADMIN_EMAIL=admin@servicemeow.local

# MCP
MCP_PATH=/mcp

# File Storage
UPLOAD_DIR=/app/uploads
MAX_UPLOAD_SIZE_MB=25

# SLA Defaults (minutes)
SLA_CRITICAL_ASSIGN=15
SLA_CRITICAL_RESOLVE=240
SLA_HIGH_ASSIGN=30
SLA_HIGH_RESOLVE=480
SLA_MEDIUM_ASSIGN=120
SLA_MEDIUM_RESOLVE=1440
SLA_LOW_ASSIGN=480
SLA_LOW_RESOLVE=4320
```

**Step 3: Create `backend/pyproject.toml`**

```toml
[project]
name = "accio-servicemeow"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "asyncpg>=0.30",
    "alembic>=1.14",
    "pydantic-settings>=2.7",
    "pyjwt>=2.10",
    "bcrypt>=4.2",
    "python-multipart>=0.0.18",
    "nh3>=0.2",
    "httpx>=0.28",
    "mcp>=1.26",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "httpx>=0.28",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

**Step 4: Create `backend/Dockerfile`**

```dockerfile
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["./entrypoint.sh"]
```

**Step 5: Create `backend/entrypoint.sh`**

```bash
#!/bin/bash
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h postgres -p 5432 -U "$POSTGRES_USER" -q; do
  sleep 1
done
echo "PostgreSQL is ready."

echo "Running database migrations..."
alembic upgrade head

echo "Checking seed data..."
python seed.py --if-empty

echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 "$@"
```

**Step 6: Create `nginx/Dockerfile`**

```dockerfile
FROM nginx:1.27-alpine

RUN apk add --no-cache openssl bash

COPY nginx.conf /etc/nginx/nginx.conf
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 443

ENTRYPOINT ["/entrypoint.sh"]
```

**Step 7: Create `nginx/entrypoint.sh`**

```bash
#!/bin/bash
set -e

CERT_DIR="/etc/nginx/certs"
CERT_FILE="$CERT_DIR/server.crt"
KEY_FILE="$CERT_DIR/server.key"

if [ ! -f "$CERT_FILE" ] || [ ! -f "$KEY_FILE" ]; then
    echo "Generating self-signed TLS certificate..."
    mkdir -p "$CERT_DIR"
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout "$KEY_FILE" \
        -out "$CERT_FILE" \
        -subj "/C=US/ST=State/L=City/O=ServiceMeow/CN=localhost"
    echo "Certificate generated."
fi

echo "Starting nginx..."
exec nginx -g "daemon off;"
```

**Step 8: Create `nginx/nginx.conf`**

```nginx
events {
    worker_connections 1024;
}

http {
    include /etc/nginx/mime.types;
    default_type application/octet-stream;

    upstream backend {
        server backend:8000;
    }

    server {
        listen 443 ssl;
        server_name localhost;

        ssl_certificate /etc/nginx/certs/server.crt;
        ssl_certificate_key /etc/nginx/certs/server.key;

        client_max_body_size 25M;

        location /api/ {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location /mcp {
            proxy_pass http://backend;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
        }

        location / {
            root /usr/share/nginx/html;
            try_files $uri $uri/ /index.html;
        }
    }
}
```

**Step 9: Create `docker-compose.yml`**

```yaml
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: ${POSTGRES_DB}
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER}"]
      interval: 5s
      timeout: 5s
      retries: 5

  backend:
    build: ./backend
    env_file: .env
    depends_on:
      postgres:
        condition: service_healthy
    volumes:
      - uploads:/app/uploads

  nginx:
    build: ./nginx
    ports:
      - "443:443"
    depends_on:
      - backend
    volumes:
      - certs:/etc/nginx/certs

volumes:
  pgdata:
  uploads:
  certs:
```

**Step 10: Create `docker-compose.dev.yml`**

```yaml
services:
  postgres:
    ports:
      - "5432:5432"

  backend:
    build: ./backend
    command: ["--reload"]
    volumes:
      - ./backend:/app
      - uploads:/app/uploads

  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - certs:/etc/nginx/certs
```

**Step 11: Commit**

```bash
git add -A
git commit -m "feat: project skeleton with Docker Compose, Nginx, and backend config"
```

---

## Task 2: FastAPI App Shell — Config, Database, Health Check

**Files:**
- Create: `backend/app/__init__.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/main.py`
- Create: `backend/app/models/__init__.py`
- Create: `backend/app/schemas/__init__.py`
- Create: `backend/app/api/__init__.py`
- Create: `backend/app/api/routes/__init__.py`
- Create: `backend/app/services/__init__.py`
- Create: `backend/app/events/__init__.py`
- Create: `backend/app/tasks/__init__.py`
- Create: `backend/app/mcp/__init__.py`
- Create: `backend/app/mcp/tools/__init__.py`

**Step 1: Create empty `__init__.py` files**

Create empty `__init__.py` in all packages listed above.

**Step 2: Create `backend/app/config.py`**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str
    postgres_user: str = "servicemeow"
    postgres_password: str = "servicemeow_secret"
    postgres_db: str = "servicemeow"

    # Auth
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    # Default Admin
    default_admin_username: str = "admin"
    default_admin_password: str = "admin"
    default_admin_email: str = "admin@servicemeow.local"

    # MCP
    mcp_path: str = "/mcp"

    # File Storage
    upload_dir: str = "/app/uploads"
    max_upload_size_mb: int = 25

    # SLA Defaults (minutes)
    sla_critical_assign: int = 15
    sla_critical_resolve: int = 240
    sla_high_assign: int = 30
    sla_high_resolve: int = 480
    sla_medium_assign: int = 120
    sla_medium_resolve: int = 1440
    sla_low_assign: int = 480
    sla_low_resolve: int = 4320

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
```

**Step 3: Create `backend/app/database.py`**

```python
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        yield session
```

**Step 4: Create `backend/app/main.py`**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app() -> FastAPI:
    app = FastAPI(title="Accio ServiceMeow", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/v1/health")
    async def health_check():
        return {"status": "ok"}

    return app


app = create_app()
```

**Step 5: Verify the app starts**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build backend postgres
```

Expect: backend starts, health check responds at `http://localhost:8000/api/v1/health`.

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: FastAPI app shell with config, database, and health check"
```

---

## Task 3: SQLAlchemy Models — Base, Enums, All Entities

**Files:**
- Create: `backend/app/models/base.py`
- Create: `backend/app/models/user.py`
- Create: `backend/app/models/group.py`
- Create: `backend/app/models/ticket.py`
- Create: `backend/app/models/ticket_note.py`
- Create: `backend/app/models/attachment.py`
- Create: `backend/app/models/audit_log.py`
- Create: `backend/app/models/api_key.py`
- Create: `backend/app/models/webhook.py`
- Create: `backend/app/models/sla_config.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Create `backend/app/models/base.py`**

```python
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=func.gen_random_uuid()
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class UserRole(str, enum.Enum):
    admin = "admin"
    manager = "manager"
    agent = "agent"


class TicketStatus(str, enum.Enum):
    open = "open"
    under_investigation = "under_investigation"
    paused = "paused"
    resolved = "resolved"


class TicketPriority(str, enum.Enum):
    critical = "critical"
    high = "high"
    medium = "medium"
    low = "low"


class ActorType(str, enum.Enum):
    user = "user"
    api_key = "api_key"
    system = "system"
```

**Step 2: Create all model files**

Create each model file per the design doc (users, groups, group_memberships, tickets, ticket_notes, attachments, audit_log, api_keys, webhooks, sla_config). Each model inherits from `Base` and uses `TimestampMixin`. Include all columns, foreign keys, indexes, and relationships as specified in the design.

Key details:
- `User` model: relationships to `GroupMembership`, `Ticket` (created), `TicketNote`, `ApiKey`
- `Group` model: relationships to `GroupMembership`, `Ticket` (assigned)
- `GroupMembership` model: composite unique on `(user_id, group_id)`
- `Ticket` model: all SLA tracking fields, indexes on `status`, `priority`, `assigned_group_id`, `assigned_user_id`, `created_at`
- `AuditLog` model: indexes on `ticket_id`, `created_at`, JSONB `metadata` column
- `SlaConfig` model: unique on `priority`

**Step 3: Update `backend/app/models/__init__.py`**

```python
from app.models.api_key import ApiKey
from app.models.attachment import Attachment
from app.models.audit_log import AuditLog
from app.models.base import ActorType, Base, TicketPriority, TicketStatus, TimestampMixin, UserRole
from app.models.group import Group, GroupMembership
from app.models.sla_config import SlaConfig
from app.models.ticket import Ticket
from app.models.ticket_note import TicketNote
from app.models.user import User
from app.models.webhook import Webhook

__all__ = [
    "ApiKey", "Attachment", "AuditLog", "ActorType", "Base",
    "TicketPriority", "TicketStatus", "TimestampMixin", "UserRole",
    "Group", "GroupMembership", "SlaConfig", "Ticket", "TicketNote",
    "User", "Webhook",
]
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: SQLAlchemy models for all entities with enums, indexes, relationships"
```

---

## Task 4: Alembic Setup and Initial Migration

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/versions/` (directory)

**Step 1: Initialize Alembic**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend alembic init alembic
```

**Step 2: Configure `backend/alembic.ini`**

Set `sqlalchemy.url` to empty (will be set from env in `env.py`).

**Step 3: Configure `backend/alembic/env.py`**

Configure for async with `asyncpg`. Import `Base` from `app.models` to pick up all models for autogenerate. Use `settings.database_url` for the connection string.

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.ext.asyncio import create_async_engine

from app.config import settings
from app.models import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(url=settings.database_url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = create_async_engine(settings.database_url)
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

**Step 4: Generate initial migration**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
    alembic revision --autogenerate -m "initial schema"
```

**Step 5: Run migration**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
    alembic upgrade head
```

Expect: all tables created in PostgreSQL.

**Step 6: Commit**

```bash
git add -A
git commit -m "feat: Alembic setup with initial migration for all tables"
```

---

## Task 5: Pydantic Schemas — Auth, Users, Groups

**Files:**
- Create: `backend/app/schemas/common.py`
- Create: `backend/app/schemas/auth.py`
- Create: `backend/app/schemas/user.py`
- Create: `backend/app/schemas/group.py`

**Step 1: Create `backend/app/schemas/common.py`**

```python
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int
    pages: int
```

**Step 2: Create `backend/app/schemas/auth.py`**

```python
from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
```

**Step 3: Create `backend/app/schemas/user.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.models.base import UserRole


class UserCreate(BaseModel):
    username: str
    email: str
    full_name: str
    password: str
    role: UserRole = UserRole.agent


class UserUpdate(BaseModel):
    email: str | None = None
    full_name: str | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserResponse(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    full_name: str
    role: UserRole
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
```

**Step 4: Create `backend/app/schemas/group.py`**

```python
import uuid
from datetime import datetime

from pydantic import BaseModel

from app.schemas.user import UserResponse


class GroupCreate(BaseModel):
    name: str
    description: str = ""


class GroupUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class GroupMemberAdd(BaseModel):
    user_id: uuid.UUID
    is_lead: bool = False


class GroupMemberResponse(BaseModel):
    user: UserResponse
    is_lead: bool
    joined_at: datetime

    model_config = {"from_attributes": True}


class GroupResponse(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class GroupDetailResponse(GroupResponse):
    members: list[GroupMemberResponse] = []
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: Pydantic schemas for auth, users, groups, and pagination"
```

---

## Task 6: Auth Service and Dependencies

**Files:**
- Create: `backend/app/services/auth_service.py`
- Create: `backend/app/api/dependencies.py`

**Step 1: Create `backend/app/services/auth_service.py`**

Implement:
- `hash_password(password: str) -> str` — bcrypt hash
- `verify_password(password: str, hashed: str) -> bool` — bcrypt verify
- `create_access_token(user_id: UUID, role: str) -> str` — JWT with `exp`, `sub`, `role`
- `create_refresh_token(user_id: UUID) -> str` — JWT with longer expiry
- `decode_token(token: str) -> dict` — decode and validate JWT
- `generate_api_key() -> tuple[str, str, str]` — returns `(plain_key, key_hash, key_prefix)`
- `verify_api_key(plain_key: str, key_hash: str) -> bool` — bcrypt verify

**Step 2: Create `backend/app/api/dependencies.py`**

Implement:
- `CurrentUser` dataclass with `user: User`, `auth_type: str`, `api_key_id: UUID | None`
- `get_current_user(authorization, api_key, db)` — FastAPI dependency, tries JWT then API key
- `require_role(*roles)` — dependency factory that checks `current_user.user.role`

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: auth service (JWT + API keys) and auth dependencies"
```

---

## Task 7: User Service and Routes

**Files:**
- Create: `backend/app/services/user_service.py`
- Create: `backend/app/api/routes/auth.py`
- Create: `backend/app/api/routes/users.py`
- Modify: `backend/app/main.py` — include routers

**Step 1: Create `backend/app/services/user_service.py`**

Implement:
- `create_user(db, data: UserCreate) -> User`
- `get_user(db, user_id: UUID) -> User | None`
- `get_user_by_username(db, username: str) -> User | None`
- `list_users(db, page, page_size) -> tuple[list[User], int]`
- `update_user(db, user_id: UUID, data: UserUpdate) -> User`

**Step 2: Create `backend/app/api/routes/auth.py`**

Routes:
- `POST /api/v1/auth/login` — validate credentials, return access token + set refresh cookie
- `POST /api/v1/auth/refresh` — read refresh cookie, issue new access token
- `POST /api/v1/auth/logout` — clear refresh cookie

**Step 3: Create `backend/app/api/routes/users.py`**

Routes:
- `POST /api/v1/users` — create user (admin only)
- `GET /api/v1/users` — list users (paginated)
- `GET /api/v1/users/{user_id}` — get user detail
- `PATCH /api/v1/users/{user_id}` — update user

**Step 4: Include routers in `main.py`**

```python
from app.api.routes import auth, users
app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/v1/users", tags=["users"])
```

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: user service with auth and user CRUD routes"
```

---

## Task 8: Group Service and Routes

**Files:**
- Create: `backend/app/services/group_service.py`
- Create: `backend/app/api/routes/groups.py`
- Modify: `backend/app/main.py` — include group router

**Step 1: Create `backend/app/services/group_service.py`**

Implement:
- `create_group(db, data: GroupCreate) -> Group`
- `get_group(db, group_id: UUID) -> Group | None` — eager load members
- `list_groups(db) -> list[Group]`
- `update_group(db, group_id: UUID, data: GroupUpdate) -> Group`
- `add_member(db, group_id: UUID, user_id: UUID, is_lead: bool) -> GroupMembership`
- `remove_member(db, group_id: UUID, user_id: UUID) -> None`

**Step 2: Create `backend/app/api/routes/groups.py`**

Routes:
- `POST /api/v1/groups` — create group
- `GET /api/v1/groups` — list groups
- `GET /api/v1/groups/{group_id}` — get group with members
- `POST /api/v1/groups/{group_id}/members` — add member
- `DELETE /api/v1/groups/{group_id}/members/{user_id}` — remove member

**Step 3: Include router in `main.py`**

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: group service with CRUD and membership management routes"
```

---

## Task 9: Integration Tests — Auth, Users, Groups

**Files:**
- Create: `backend/tests/__init__.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_users.py`
- Create: `backend/tests/test_groups.py`

**Step 1: Create `backend/tests/conftest.py`**

```python
import asyncio
from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.database import get_db
from app.main import create_app
from app.models import Base

# Use a separate test database
TEST_DB_URL = settings.database_url.replace("/servicemeow", "/servicemeow_test")

engine = create_async_engine(TEST_DB_URL)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    async with TestSession() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac
```

**Step 2: Create `backend/tests/test_auth.py`**

Test cases:
- Login with valid credentials returns access token
- Login with invalid credentials returns 401
- Refresh with valid cookie returns new access token
- Accessing protected route without token returns 401

**Step 3: Create `backend/tests/test_users.py`**

Test cases:
- Admin can create a user
- Non-admin cannot create a user (403)
- List users returns paginated results
- Get user by ID returns user detail
- Update user changes fields

**Step 4: Create `backend/tests/test_groups.py`**

Test cases:
- Create group returns group
- List groups returns all groups
- Get group detail includes members
- Add member to group
- Remove member from group
- Add duplicate member returns error

**Step 5: Run tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
    pytest tests/ -v
```

Expect: all tests pass.

**Step 6: Commit**

```bash
git add -A
git commit -m "test: integration tests for auth, users, and groups"
```

---

## Task 10: Pydantic Schemas — Tickets, Notes, Attachments, Audit Log

**Files:**
- Create: `backend/app/schemas/ticket.py`
- Create: `backend/app/schemas/ticket_note.py`
- Create: `backend/app/schemas/attachment.py`
- Create: `backend/app/schemas/audit_log.py`
- Create: `backend/app/schemas/dashboard.py`
- Create: `backend/app/schemas/api_key.py`
- Create: `backend/app/schemas/webhook.py`

**Step 1: Create ticket schemas**

- `TicketCreate`: title, description, priority, assigned_group_id?, assigned_user_id?
- `TicketUpdate`: title?, description?, status?, priority?, assigned_group_id?, assigned_user_id?
- `TicketResponse`: all fields + SLA status (elapsed, breached, at_risk)
- `TicketListResponse`: subset of fields for list view
- `TicketDetailResponse`: full ticket + notes + attachments + audit log

**Step 2: Create remaining schema files**

Each with Create, Update (where applicable), and Response models matching the design doc.

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: Pydantic schemas for tickets, notes, attachments, audit log, dashboard, API keys, webhooks"
```

---

## Task 11: Audit Service

**Files:**
- Create: `backend/app/services/audit_service.py`

**Step 1: Create `backend/app/services/audit_service.py`**

Implement:
- `log_action(db, ticket_id, actor_id, actor_type, action, field_changed?, old_value?, new_value?, metadata?) -> AuditLog`
- `get_audit_log(db, ticket_id) -> list[AuditLog]` — ordered by created_at desc

This is a simple append-only service called by ticket/note services.

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: audit service for ticket change tracking"
```

---

## Task 12: Ticket Service

**Files:**
- Create: `backend/app/services/ticket_service.py`

**Step 1: Implement ticket service**

Functions:
- `create_ticket(db, current_user, data: TicketCreate) -> Ticket`
  - Auto-generate ticket number (`ASM-{sequence}`)
  - Look up SLA target from `sla_config` table based on priority
  - Set `sla_target_minutes`, `created_by_id`
  - Log audit: "created"
- `get_ticket(db, ticket_id: UUID) -> Ticket | None`
  - Eager load notes, attachments, audit log
- `get_ticket_by_number(db, ticket_number: str) -> Ticket | None`
- `update_ticket(db, current_user, ticket_id, data: TicketUpdate) -> Ticket`
  - Track status transitions: pause/unpause logic
  - On pause: set `paused_at`
  - On unpause: add delta to `total_paused_seconds`, clear `paused_at`
  - On first assignment: set `first_assigned_at`
  - On resolve: set `resolved_at`
  - Log audit for each changed field
- `list_tickets(db, filters, page, page_size) -> tuple[list[Ticket], int]`
  - Filter by status, priority, group, user, search (tsvector), sla_breached
  - Sort by any field, default created_at desc
- `soft_delete_ticket(db, current_user, ticket_id) -> None`

**Step 2: Implement ticket number generation**

Use a PostgreSQL sequence:
```sql
CREATE SEQUENCE ticket_number_seq START 1;
```
Add this to the Alembic migration or generate it in the service on first use.
Format: `ASM-{nextval:04d}`

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: ticket service with CRUD, SLA tracking, status transitions, search"
```

---

## Task 13: Note and Attachment Services

**Files:**
- Create: `backend/app/services/note_service.py`
- Create: `backend/app/services/attachment_service.py`

**Step 1: Create `backend/app/services/note_service.py`**

Implement:
- `add_note(db, current_user, ticket_id, content, is_internal) -> TicketNote`
  - Sanitize HTML with `nh3`
  - Log audit: "note_added"
- `edit_note(db, current_user, note_id, content) -> TicketNote`
  - Sanitize HTML
- `list_notes(db, ticket_id) -> list[TicketNote]`

**Step 2: Create `backend/app/services/attachment_service.py`**

Implement:
- `upload_file(db, current_user, ticket_id, file: UploadFile, note_id?) -> Attachment`
  - Validate file type (images, docs, archives) and size (max 25MB)
  - Stream to disk at `{UPLOAD_DIR}/{ticket_id}/{uuid}_{original_filename}`
  - Log audit: "file_uploaded"
- `list_attachments(db, ticket_id) -> list[Attachment]`
- `get_attachment(db, attachment_id) -> Attachment | None`
- `delete_attachment(db, current_user, attachment_id) -> None`
  - Remove file from disk + DB record
  - Log audit: "file_deleted"

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: note service with HTML sanitization and attachment service with file streaming"
```

---

## Task 14: Ticket Routes

**Files:**
- Create: `backend/app/api/routes/tickets.py`
- Modify: `backend/app/main.py` — include ticket router

**Step 1: Create `backend/app/api/routes/tickets.py`**

Routes:
- `POST /api/v1/tickets` — create ticket
- `GET /api/v1/tickets` — list with filters/pagination (query params: status, priority, assigned_group_id, assigned_user_id, created_by_id, search, sla_breached, sort_by, sort_order, page, page_size)
- `GET /api/v1/tickets/{ticket_id}` — detail with notes, attachments, audit log
- `PATCH /api/v1/tickets/{ticket_id}` — update
- `DELETE /api/v1/tickets/{ticket_id}` — soft delete
- `POST /api/v1/tickets/{ticket_id}/notes` — add note
- `GET /api/v1/tickets/{ticket_id}/notes` — list notes
- `PATCH /api/v1/tickets/{ticket_id}/notes/{note_id}` — edit note
- `POST /api/v1/tickets/{ticket_id}/attachments` — upload file(s)
- `GET /api/v1/tickets/{ticket_id}/attachments` — list attachments
- `GET /api/v1/attachments/{attachment_id}/download` — download file
- `DELETE /api/v1/attachments/{attachment_id}` — remove attachment
- `GET /api/v1/tickets/{ticket_id}/audit-log` — audit trail

**Step 2: Include router in `main.py`**

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: ticket routes with full CRUD, notes, attachments, and audit log"
```

---

## Task 15: SLA Service and Background Task

**Files:**
- Create: `backend/app/services/sla_service.py`
- Create: `backend/app/tasks/sla_checker.py`
- Modify: `backend/app/main.py` — start background task on startup

**Step 1: Create `backend/app/services/sla_service.py`**

Implement:
- `calculate_elapsed_seconds(ticket: Ticket) -> int` — `now - created_at - total_paused_seconds` (account for currently paused)
- `is_breached(ticket: Ticket) -> bool` — elapsed > target
- `is_at_risk(ticket: Ticket) -> bool` — elapsed > 80% of target
- `get_sla_status(ticket: Ticket) -> dict` — `{elapsed_seconds, target_seconds, breached, at_risk, percentage}`
- `get_mtta(db, group_id?, priority?, date_from?, date_to?) -> float` — avg(first_assigned_at - created_at)
- `get_mttr(db, group_id?, priority?, date_from?, date_to?) -> float` — avg(resolved_at - created_at - total_paused_seconds)

**Step 2: Create `backend/app/tasks/sla_checker.py`**

```python
import asyncio
import logging

from app.database import async_session

logger = logging.getLogger(__name__)


async def check_sla_breaches():
    """Runs every 60 seconds, checks open tickets for SLA breaches."""
    while True:
        try:
            async with async_session() as db:
                # Query open tickets where SLA is breached
                # Flag breached tickets (add sla_breached=True or similar)
                # Emit ticket.sla_breached webhook (once per breach)
                pass
        except Exception:
            logger.exception("SLA check failed")
        await asyncio.sleep(60)
```

**Step 3: Start background task in `main.py`**

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(check_sla_breaches())
    yield
    task.cancel()
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: SLA service with breach detection background task"
```

---

## Task 16: Dashboard Routes

**Files:**
- Create: `backend/app/api/routes/dashboard.py`
- Modify: `backend/app/main.py` — include dashboard router

**Step 1: Create `backend/app/api/routes/dashboard.py`**

Routes:
- `GET /api/v1/dashboard/summary` — ticket counts by status, group, priority
- `GET /api/v1/dashboard/sla` — MTTA/MTTR by group/priority (query params: group_id, priority, date_from, date_to)
- `GET /api/v1/dashboard/activity` — recent audit log entries across all tickets (paginated, default last 50)

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: dashboard routes with summary, SLA metrics, and activity feed"
```

---

## Task 17: API Key Routes

**Files:**
- Create: `backend/app/api/routes/api_keys.py`
- Modify: `backend/app/main.py` — include api_keys router

**Step 1: Create API key service functions in `auth_service.py`**

Add to existing auth service:
- `create_api_key(db, current_user, name) -> tuple[ApiKey, str]` — returns model + plain key (shown once)
- `list_api_keys(db, current_user) -> list[ApiKey]`
- `revoke_api_key(db, current_user, key_id) -> None`

**Step 2: Create `backend/app/api/routes/api_keys.py`**

Routes:
- `POST /api/v1/api-keys` — create, returns plain key once
- `GET /api/v1/api-keys` — list (prefix + metadata only)
- `DELETE /api/v1/api-keys/{key_id}` — revoke

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: API key management routes"
```

---

## Task 18: Webhook Service, Dispatcher, and Routes

**Files:**
- Create: `backend/app/services/webhook_service.py`
- Create: `backend/app/events/dispatcher.py`
- Create: `backend/app/api/routes/webhooks.py`
- Modify: `backend/app/main.py` — include webhooks router

**Step 1: Create `backend/app/services/webhook_service.py`**

Implement:
- `create_webhook(db, current_user, data) -> Webhook`
- `list_webhooks(db) -> list[Webhook]`
- `update_webhook(db, webhook_id, data) -> Webhook`
- `delete_webhook(db, webhook_id) -> None`

**Step 2: Create `backend/app/events/dispatcher.py`**

```python
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone

import httpx

from app.database import async_session

logger = logging.getLogger(__name__)


async def dispatch_event(event_type: str, payload: dict):
    """Query matching webhook subscriptions and fire HTTP POSTs."""
    async with async_session() as db:
        # Query active webhooks where event_type in webhook.events
        # For each match, fire _deliver_webhook as a background task
        pass


async def _deliver_webhook(url: str, secret: str, event_type: str, payload: dict):
    """Deliver webhook with HMAC signing and retry logic."""
    body = json.dumps({
        "event": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": payload,
    })
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    headers = {
        "Content-Type": "application/json",
        "X-ServiceMeow-Signature": signature,
    }

    delays = [1, 5, 30]
    async with httpx.AsyncClient() as client:
        for attempt, delay in enumerate(delays):
            try:
                response = await client.post(url, content=body, headers=headers, timeout=10)
                if response.is_success:
                    return
            except Exception:
                logger.warning(f"Webhook delivery attempt {attempt + 1} failed for {url}")
            if attempt < len(delays) - 1:
                await asyncio.sleep(delay)
    logger.error(f"Webhook delivery failed after {len(delays)} attempts for {url}")
```

**Step 3: Create webhook routes**

Routes:
- `POST /api/v1/webhooks` — register
- `GET /api/v1/webhooks` — list
- `PATCH /api/v1/webhooks/{webhook_id}` — update
- `DELETE /api/v1/webhooks/{webhook_id}` — remove

**Step 4: Wire dispatcher into ticket service**

After ticket mutations (create, update, assign, resolve, note_added), call `dispatch_event()` with the appropriate event type.

**Step 5: Commit**

```bash
git add -A
git commit -m "feat: webhook system with HMAC-signed delivery, retry logic, and CRUD routes"
```

---

## Task 19: Integration Tests — Tickets

**Files:**
- Create: `backend/tests/test_tickets.py`

**Step 1: Write ticket integration tests**

Test cases:
- Create ticket returns ticket with generated number
- List tickets with pagination
- Filter tickets by status, priority, group
- Search tickets by title/description
- Get ticket detail includes notes and audit log
- Update ticket status tracks transitions
- Pause/unpause tracks SLA correctly
- Assign ticket sets first_assigned_at on first assignment
- Resolve ticket sets resolved_at
- Add note to ticket
- Edit note
- Upload attachment
- List attachments
- Download attachment
- Delete attachment
- Get audit log shows all changes
- Soft delete ticket

**Step 2: Run tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
    pytest tests/test_tickets.py -v
```

Expect: all tests pass.

**Step 3: Commit**

```bash
git add -A
git commit -m "test: integration tests for ticket CRUD, notes, attachments, SLA, audit log"
```

---

## Task 20: MCP Server Setup and Ticket Tools

**Files:**
- Create: `backend/app/mcp/server.py`
- Create: `backend/app/mcp/tools/tickets.py`
- Modify: `backend/app/main.py` — mount MCP app with lifespan

**Step 1: Create `backend/app/mcp/server.py`**

```python
from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "ServiceMeow",
    stateless_http=True,
    json_response=True,
)
```

**Step 2: Create `backend/app/mcp/tools/tickets.py`**

Register tools on the `mcp` instance using `@mcp.tool()` decorators:

- `create_ticket(title, description, priority, assigned_group_id?, assigned_user_id?)` — calls ticket_service
- `get_ticket(ticket_id_or_number)` — accepts UUID or ASM-XXXX format
- `update_ticket(ticket_id, title?, description?, status?, priority?)` — partial update
- `assign_ticket(ticket_id, group_id?, user_id?)` — assign/reassign
- `list_tickets(status?, priority?, group_id?, user_id?, search?, sla_breached?, page?, page_size?)` — filtered list
- `add_ticket_note(ticket_id, content, is_internal?)` — add note
- `resolve_ticket(ticket_id, resolution_note?)` — convenience resolve
- `bulk_update_tickets(ticket_ids, status?, group_id?, user_id?)` — batch update

Each tool:
- Extracts API key from MCP context headers
- Creates a DB session
- Authenticates via the API key
- Calls the appropriate service
- Returns `{"summary": "...", "data": {...}}`
- Returns actionable error messages on failure

**Step 3: Mount MCP in `main.py`**

Update the lifespan to include `mcp.session_manager.run()`:

```python
import contextlib
from app.mcp.server import mcp
from app.mcp.tools import tickets  # noqa: F401 — registers tools on import

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    async with contextlib.AsyncExitStack() as stack:
        await stack.enter_async_context(mcp.session_manager.run())
        sla_task = asyncio.create_task(check_sla_breaches())
        yield
        sla_task.cancel()

app = FastAPI(title="Accio ServiceMeow", version="0.1.0", lifespan=lifespan)
app.mount("/mcp", mcp.streamable_http_app())
```

**Step 4: Commit**

```bash
git add -A
git commit -m "feat: MCP server with ticket management tools mounted at /mcp"
```

---

## Task 21: MCP Information Tools

**Files:**
- Create: `backend/app/mcp/tools/info.py`
- Modify: `backend/app/main.py` — import info tools

**Step 1: Create `backend/app/mcp/tools/info.py`**

Register tools:
- `get_dashboard_summary()` — counts by status/priority/group
- `get_sla_metrics(group_id?, priority?, date_from?, date_to?)` — MTTA/MTTR
- `list_groups()` — groups with member counts
- `list_users(group_id?)` — users, optionally filtered
- `get_ticket_audit_log(ticket_id)` — full audit trail

Each follows the same pattern: auth from headers, DB session, service call, structured response.

**Step 2: Import in main.py**

Add `from app.mcp.tools import info  # noqa: F401` alongside the tickets import.

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: MCP information tools (dashboard, SLA, groups, users, audit log)"
```

---

## Task 22: MCP Integration Tests

**Files:**
- Create: `backend/tests/test_mcp.py`

**Step 1: Write MCP integration tests**

Test the MCP endpoint directly via HTTP POST to `/mcp`:

- Tool discovery (list tools) returns all registered tools
- `create_ticket` creates a ticket and returns structured response
- `get_ticket` retrieves by ticket number (ASM-XXXX format)
- `list_tickets` with filters returns filtered results
- `assign_ticket` assigns and sets first_assigned_at
- `add_ticket_note` adds a note
- `resolve_ticket` resolves with note
- `get_dashboard_summary` returns counts
- MCP request without API key returns auth error
- MCP request with invalid API key returns auth error

**Step 2: Run tests**

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml exec backend \
    pytest tests/test_mcp.py -v
```

**Step 3: Commit**

```bash
git add -A
git commit -m "test: MCP server integration tests"
```

---

## Task 23: Seed Script

**Files:**
- Create: `backend/seed.py`

**Step 1: Create `backend/seed.py`**

```python
"""Seed script for demo data. Run with --if-empty to skip if data exists."""
import argparse
import asyncio
import sys

from app.config import settings
from app.database import async_session
from app.models import User, Group, GroupMembership, SlaConfig, ApiKey
from app.models.base import UserRole, TicketPriority
from app.services.auth_service import hash_password, generate_api_key


GROUPS = [
    {"name": "IT Operations", "description": "General IT support and operations"},
    {"name": "Cybersecurity", "description": "Security monitoring, incident response, and compliance"},
    {"name": "Server Infrastructure", "description": "Server provisioning, maintenance, and monitoring"},
    {"name": "Desktop Support", "description": "End-user device support and software deployment"},
]

USERS = [
    {"username": "jchen", "full_name": "Jessica Chen", "email": "jchen@servicemeow.local", "role": UserRole.manager, "group": "IT Operations", "is_lead": True},
    {"username": "mwilliams", "full_name": "Marcus Williams", "email": "mwilliams@servicemeow.local", "role": UserRole.agent, "group": "IT Operations"},
    {"username": "spatel", "full_name": "Sanjay Patel", "email": "spatel@servicemeow.local", "role": UserRole.manager, "group": "Cybersecurity", "is_lead": True},
    {"username": "akim", "full_name": "Alice Kim", "email": "akim@servicemeow.local", "role": UserRole.agent, "group": "Cybersecurity"},
    {"username": "troberts", "full_name": "Tyler Roberts", "email": "troberts@servicemeow.local", "role": UserRole.manager, "group": "Server Infrastructure", "is_lead": True},
    {"username": "lgarcia", "full_name": "Luna Garcia", "email": "lgarcia@servicemeow.local", "role": UserRole.agent, "group": "Server Infrastructure"},
    {"username": "dthompson", "full_name": "Derek Thompson", "email": "dthompson@servicemeow.local", "role": UserRole.manager, "group": "Desktop Support", "is_lead": True},
    {"username": "nwright", "full_name": "Nina Wright", "email": "nwright@servicemeow.local", "role": UserRole.agent, "group": "Desktop Support"},
]

SLA_DEFAULTS = [
    {"priority": TicketPriority.critical, "target_assign_minutes": settings.sla_critical_assign, "target_resolve_minutes": settings.sla_critical_resolve},
    {"priority": TicketPriority.high, "target_assign_minutes": settings.sla_high_assign, "target_resolve_minutes": settings.sla_high_resolve},
    {"priority": TicketPriority.medium, "target_assign_minutes": settings.sla_medium_assign, "target_resolve_minutes": settings.sla_medium_resolve},
    {"priority": TicketPriority.low, "target_assign_minutes": settings.sla_low_assign, "target_resolve_minutes": settings.sla_low_resolve},
]


async def seed():
    async with async_session() as db:
        # Check if already seeded
        existing = await db.execute(select(User).where(User.username == settings.default_admin_username))
        if existing.scalar_one_or_none():
            print("Database already seeded. Skipping.")
            return

        # Create admin user
        admin = User(
            username=settings.default_admin_username,
            email=settings.default_admin_email,
            full_name="System Administrator",
            hashed_password=hash_password(settings.default_admin_password),
            role=UserRole.admin,
        )
        db.add(admin)

        # Create groups
        group_map = {}
        for g in GROUPS:
            group = Group(**g)
            db.add(group)
            group_map[g["name"]] = group

        await db.flush()

        # Create users and memberships
        for u in USERS:
            group_name = u.pop("group")
            is_lead = u.pop("is_lead", False)
            user = User(hashed_password=hash_password("password123"), **u)
            db.add(user)
            await db.flush()
            membership = GroupMembership(user_id=user.id, group_id=group_map[group_name].id, is_lead=is_lead)
            db.add(membership)

        # Create SLA config
        for s in SLA_DEFAULTS:
            db.add(SlaConfig(**s))

        # Create API key for Claude MCP Agent
        plain_key, key_hash, key_prefix = generate_api_key()
        api_key = ApiKey(
            name="Claude MCP Agent",
            key_hash=key_hash,
            key_prefix=key_prefix,
            user_id=admin.id,
        )
        db.add(api_key)

        await db.commit()

        print("=" * 60)
        print("Seed data created successfully!")
        print(f"Admin user: {settings.default_admin_username}")
        print(f"MCP API Key: {plain_key}")
        print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--if-empty", action="store_true", help="Only seed if database is empty")
    args = parser.parse_args()
    asyncio.run(seed())
```

**Step 2: Commit**

```bash
git add -A
git commit -m "feat: seed script with demo users, groups, SLA config, and MCP API key"
```

---

## Task 24: Rate Limiting Middleware

**Files:**
- Create: `backend/app/api/middleware.py`
- Modify: `backend/app/main.py` — add middleware

**Step 1: Create `backend/app/api/middleware.py`**

Implement in-memory sliding window rate limiter for API key requests:
- Track requests per API key prefix in a dict with timestamps
- 100 requests per minute per key
- Return 429 Too Many Requests when exceeded

**Step 2: Add middleware to app in `main.py`**

**Step 3: Commit**

```bash
git add -A
git commit -m "feat: API key rate limiting middleware (100 req/min)"
```

---

## Task 25: End-to-End Smoke Test

**Step 1: Build and start everything**

```bash
cp .env.example .env
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build -d
```

**Step 2: Verify services**

- Health check: `curl -k https://localhost/api/v1/health`
- Login: `curl -k -X POST https://localhost/api/v1/auth/login -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin"}'`
- List groups (with token): `curl -k https://localhost/api/v1/groups -H 'Authorization: Bearer <token>'`
- MCP tool listing (with API key): `curl -k -X POST https://localhost/mcp -H 'api_key: <key>' -H 'Content-Type: application/json' -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'`

**Step 3: Verify seed data printed API key to logs**

```bash
docker compose logs backend | grep "MCP API Key"
```

**Step 4: Commit any fixes**

```bash
git add -A
git commit -m "fix: smoke test fixes"
```

---

Plan complete and saved to `docs/plans/2026-02-05-accio-servicemeow-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (this session)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** — Open a new session with executing-plans, batch execution with checkpoints

Which approach?