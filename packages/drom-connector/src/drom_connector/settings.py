"""baza.drom.ru connector runtime settings (env-driven via DROM_ prefix).

Env vars (all optional):
  DROM_TIMEOUT         - per-tier HTTP/CDP timeout seconds, default 25.0
  DROM_MAX_BODY_BYTES  - hard cap on any HTTP response body, default 50 MiB
  DROM_MIN_GAP         - polite inter-request gap seconds, default 2.0
  DROM_IMPERSONATE     - curl_cffi fingerprint profile, default "chrome124"
  DROM_CACHE_TTL       - seconds to cache upstream reads, 0 disables, default 120.0
  DROM_PROXY           - proxy URL for tier-1 fetch, default unset (honours HTTPS_PROXY)
  DROM_DEFAULT_CITY    - default city slug (e.g. "vladivostok", "moskva"), default "" (all regions)
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

_DEFAULT_MAX_BODY_BYTES = 50 * 1024 * 1024


class DromSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="DROM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    timeout: float = Field(default=25.0, gt=0)
    max_body_bytes: int = Field(default=_DEFAULT_MAX_BODY_BYTES, gt=0)
    min_gap: float = Field(default=2.0, ge=0)
    impersonate: str = Field(default="chrome124", min_length=1)
    cache_ttl: float = Field(
        default=120.0,
        ge=0,
        description="Seconds to cache upstream reads. 0 disables caching.",
    )
    proxy: SecretStr = Field(
        default=SecretStr(""),
        description=(
            "Optional proxy URL for tier-1 fetch. Empty honours HTTPS_PROXY/ALL_PROXY. "
            "May carry user:pass credentials, so it is a SecretStr: repr/dump show '**********', "
            "and only the outbound fetch ever unwraps it."
        ),
    )
    default_city: str = Field(
        default="",
        description="Default city slug (e.g. 'vladivostok', 'moskva'). Empty means all regions.",
    )


@lru_cache(maxsize=1)
def get_settings() -> DromSettings:
    return DromSettings()
