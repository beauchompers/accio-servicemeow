import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.mcp.auth as mcp_auth
import app.mcp.tools.tickets as mcp_tickets
import app.mcp.tools.info as mcp_info
from app.config import settings
from app.database import get_db
from app.main import create_app
from app.mcp.server import mcp
from app.models import Base
from app.models.base import TicketPriority, UserRole
from app.models.group import Group, GroupMembership
from app.models.sla_config import SlaConfig
from app.models.user import User
from app.services.auth_service import create_access_token, hash_password

# Derive a test database URL from the configured DATABASE_URL by appending _test.
# For example: postgresql+asyncpg://user:pass@host/servicemeow -> ...servicemeow_test
_base_url = settings.database_url
if _base_url.endswith("/"):
    TEST_DB_URL = _base_url + "servicemeow_test"
else:
    TEST_DB_URL = _base_url + "_test"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSession = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def _mcp_session():
    """Start the MCP session manager once for the entire test session."""
    cm = mcp.session_manager.run()
    await cm.__aenter__()
    yield
    try:
        await cm.__aexit__(None, None, None)
    except RuntimeError:
        pass  # anyio task boundary mismatch during teardown is expected


@pytest.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test and drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Create sequence used by ticket_service (not in SQLAlchemy models)
        await conn.execute(
            text("CREATE SEQUENCE IF NOT EXISTS ticket_number_seq START 1")
        )
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.execute(text("DROP SEQUENCE IF EXISTS ticket_number_seq"))
    await engine.dispose()


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Provide a test database session."""
    async with TestSession() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Provide an async HTTP client wired to the FastAPI app with test DB override."""
    app = create_app()

    async def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db

    # Patch MCP tools to use the test session instead of their own
    @asynccontextmanager
    async def _test_session():
        yield db

    saved = (mcp_tickets.async_session, mcp_info.async_session, mcp_auth.async_session)
    mcp_tickets.async_session = _test_session
    mcp_info.async_session = _test_session
    mcp_auth.async_session = _test_session

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac

    mcp_tickets.async_session, mcp_info.async_session, mcp_auth.async_session = saved


@pytest.fixture
async def admin_user(db: AsyncSession) -> User:
    """Create and return an admin user."""
    user = User(
        username="testadmin",
        email="testadmin@test.com",
        full_name="Test Admin",
        hashed_password=hash_password("adminpass"),
        role=UserRole.admin,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
async def agent_user(db: AsyncSession) -> User:
    """Create and return an agent user."""
    user = User(
        username="testagent",
        email="testagent@test.com",
        full_name="Test Agent",
        hashed_password=hash_password("agentpass"),
        role=UserRole.agent,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest.fixture
def admin_token(admin_user: User) -> str:
    """Return a valid JWT access token for the admin user."""
    return create_access_token(admin_user.id, admin_user.role.value)


@pytest.fixture
def agent_token(agent_user: User) -> str:
    """Return a valid JWT access token for the agent user."""
    return create_access_token(agent_user.id, agent_user.role.value)


@pytest.fixture
async def test_group(db: AsyncSession) -> Group:
    """Create and return a test group."""
    group = Group(name="Test Group", description="A group for testing")
    db.add(group)
    await db.commit()
    await db.refresh(group)
    return group


@pytest.fixture
async def admin_in_group(db: AsyncSession, admin_user: User, test_group: Group) -> GroupMembership:
    """Add the admin user to the test group and return the membership."""
    membership = GroupMembership(user_id=admin_user.id, group_id=test_group.id)
    db.add(membership)
    await db.commit()
    await db.refresh(membership)
    return membership


@pytest.fixture
async def sla_config(db: AsyncSession) -> list[SlaConfig]:
    """Create SLA configs for all priorities with both MTTA and MTTR targets."""
    configs = []
    targets = {
        TicketPriority.critical: (15, 120),
        TicketPriority.high: (30, 240),
        TicketPriority.medium: (60, 480),
        TicketPriority.low: (120, 1440),
    }
    for priority, (assign_min, resolve_min) in targets.items():
        config = SlaConfig(
            priority=priority,
            target_assign_minutes=assign_min,
            target_resolve_minutes=resolve_min,
        )
        db.add(config)
        configs.append(config)
    await db.commit()
    return configs


def auth_header(token: str) -> dict:
    """Helper to create Authorization header."""
    return {"Authorization": f"Bearer {token}"}
