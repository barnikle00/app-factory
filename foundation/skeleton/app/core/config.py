"""Every address, limit, timeout and interval in this application (ADR 0007).

One settings class per domain, every field typed and named with its unit. Code reads
`get_settings()`; nothing else in `app/` reads the environment. A new domain gets its own class
here when the phase that needs it arrives — never a literal in the code that uses it.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# Facts of the calendar, not tunables.
SECONDS_PER_HOUR = 3_600


class DatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DB_", env_file=".env", extra="ignore")

    dsn: str = "postgresql+asyncpg://app@127.0.0.1:5432/app"
    pool_size_count: int = 5
    pool_overflow_count: int = 5
    pool_timeout_seconds: float = 10.0
    connect_timeout_seconds: float = 5.0
    statement_timeout_seconds: float = 30.0
    list_max_rows_count: int = 500


class WebSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="WEB_", env_file=".env", extra="ignore")

    bind_host: str = "127.0.0.1"
    bind_port_number: int = 8000
    readiness_check_timeout_seconds: float = 3.0
    job_overdue_grace_seconds: float = 120.0


class AuthSettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="AUTH_", env_file=".env", extra="ignore")

    # A secret: set in the environment of `web`, never in a file in the repository.
    session_signing_key: str = ""
    session_cookie_name: str = "session"
    session_idle_timeout_hours: int = 12
    session_cookie_secure: bool = True
    initial_password_length_chars: int = 16
    password_hash_time_cost_count: int = 3
    password_hash_memory_cost_kib: int = 65_536
    password_hash_parallelism_count: int = 2


class ObservabilitySettings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OBS_", env_file=".env", extra="ignore")

    log_level: str = "INFO"
    log_as_json: bool = True
    jobs_metrics_port_number: int = 9101


class OutsideSettings(BaseSettings):
    """The guard on every write to an outside system (ADR 0010).

    `ceilings` and `repeat_limits` override the defaults per target, e.g.
    OUTSIDE_CEILINGS='{"telegram": 60}'. A target not named gets the default.
    """

    model_config = SettingsConfigDict(env_prefix="OUTSIDE_", env_file=".env", extra="ignore")

    default_hourly_ceiling_count: int = 120
    default_repeat_limit_count: int = 3
    ceilings: dict[str, int] = {}
    repeat_limits: dict[str, int] = {}

    def ceiling_for(self, target: str) -> int:
        return self.ceilings.get(target, self.default_hourly_ceiling_count)

    def repeat_limit_for(self, target: str) -> int:
        return self.repeat_limits.get(target, self.default_repeat_limit_count)


class DisplaySettings(BaseSettings):
    """How a person reads what the database stores. Stored instants stay UTC (ADR 0003)."""

    model_config = SettingsConfigDict(env_prefix="DISPLAY_", env_file=".env", extra="ignore")

    # An IANA zone name such as "Europe/Berlin". Empty means the language profile's default,
    # or UTC when the app has no profile.
    timezone_name: str = ""


class TimingSettings(BaseSettings):
    """How often each scheduled job runs. One field per job, added with the job."""

    model_config = SettingsConfigDict(env_prefix="TIMING_", env_file=".env", extra="ignore")


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    web: WebSettings
    auth: AuthSettings
    observability: ObservabilitySettings
    outside: OutsideSettings
    display: DisplaySettings
    timing: TimingSettings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings(
        database=DatabaseSettings(),
        web=WebSettings(),
        auth=AuthSettings(),
        observability=ObservabilitySettings(),
        outside=OutsideSettings(),
        display=DisplaySettings(),
        timing=TimingSettings(),
    )
