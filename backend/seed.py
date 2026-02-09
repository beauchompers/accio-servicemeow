"""Seed script for demo data. Run with: python seed.py [--if-empty]"""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select

from app.config import settings
from app.database import async_session
from app.models import User, Group, GroupMembership, SlaConfig, ApiKey
from app.models.base import UserRole, TicketPriority
from app.services.auth_service import hash_password, generate_api_key

SEED_PATHS = [
    Path("/config/seed.json"),
    Path(__file__).resolve().parent / "seed.json",
]


def load_seed_data() -> tuple[list[dict], list[dict]]:
    """Load groups and users from seed.json. Returns empty lists if not found."""
    seed_file = next((p for p in SEED_PATHS if p.exists()), None)
    if seed_file is None:
        print("No seed.json found — skipping demo users/groups.")
        return [], []

    with open(seed_file) as f:
        data = json.load(f)

    groups = data.get("groups", [])
    users = data.get("users", [])
    print(f"Loaded {len(groups)} groups and {len(users)} users from seed.json")
    return groups, users


SLA_DEFAULTS = [
    {"priority": TicketPriority.critical, "target_assign_minutes": settings.sla_critical_assign, "target_resolve_minutes": settings.sla_critical_resolve},
    {"priority": TicketPriority.high, "target_assign_minutes": settings.sla_high_assign, "target_resolve_minutes": settings.sla_high_resolve},
    {"priority": TicketPriority.medium, "target_assign_minutes": settings.sla_medium_assign, "target_resolve_minutes": settings.sla_medium_resolve},
    {"priority": TicketPriority.low, "target_assign_minutes": settings.sla_low_assign, "target_resolve_minutes": settings.sla_low_resolve},
]


async def seed():
    async with async_session() as db:
        # Check if already seeded
        existing = await db.execute(
            select(User).where(User.username == settings.default_admin_username)
        )
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

        # Load seed data from JSON
        seed_groups, seed_users = load_seed_data()

        # Create groups
        group_map = {}
        for g in seed_groups:
            group = Group(**g)
            db.add(group)
            group_map[g["name"]] = group

        await db.flush()

        # Create users and memberships
        for u in seed_users:
            password = u.get("password", "password123")
            group_name = u.get("group")
            is_lead = u.get("is_lead", False)
            user_data = {
                k: v for k, v in u.items()
                if k not in ("group", "is_lead", "password")
            }
            user_data["role"] = UserRole(user_data["role"])
            user = User(hashed_password=hash_password(password), **user_data)
            db.add(user)
            await db.flush()
            if group_name and group_name in group_map:
                membership = GroupMembership(
                    user_id=user.id,
                    group_id=group_map[group_name].id,
                    is_lead=is_lead,
                )
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
    parser.parse_args()
    asyncio.run(seed())
