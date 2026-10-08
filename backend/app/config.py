"""All configuration comes from environment variables (see .env.example)."""
import logging
import secrets
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger("cloudsentry.config")


def _split(value: str) -> list[str]:
    return [v.strip() for v in value.split(",") if v.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = ""
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    instance_id: str = "API-01"
    expected_instances: str = "API-01,API-02"
    register_instances: str = ""
    heartbeat_seconds: int = 10

    environment: str = "development"
    auto_seed: bool = True
    seed_records: int = 2500
    seed_admin_password: str = ""
    seed_analyst_password: str = ""
    trust_proxy_headers: bool = True

    @property
    def cors_list(self) -> list[str]:
        return _split(self.cors_origins)

    @property
    def expected_list(self) -> list[str]:
        return _split(self.expected_instances)

    @property
    def registered_list(self) -> list[str]:
        return _split(self.register_instances) or [self.instance_id]

    @property
    def virtual_mode(self) -> bool:
        """True when ONE process plays several logical instances."""
        return len(self.registered_list) > 1

    @property
    def db_url(self) -> str:
        return self.database_url or "sqlite:///./cloudsentry.db"


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    if not s.jwt_secret:
        if s.environment.lower() == "production":
            raise RuntimeError("JWT_SECRET must be set when ENVIRONMENT=production")
        s.jwt_secret = secrets.token_urlsafe(48)
        log.warning("JWT_SECRET not set - generated a temporary one (tokens reset on restart; "
                    "set JWT_SECRET when running multiple instances).")
    return s


settings = get_settings()
