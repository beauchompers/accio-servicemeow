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

    # CORS
    allowed_origins: list[str] = ["https://localhost:8889"]

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
