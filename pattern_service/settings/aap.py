# from urllib.parse import urlparse
# from typing import Optional
# from pydantic import Field
# from pydantic import field_validator
# from pydantic_settings import BaseSettings, SettingsConfigDict
# from functools import lru_cache

# class AAPSettings(BaseSettings):
#     # AAP_INTERNAL_URL: For internal service-to-service communication
#     internal_url: Optional[str] = Field(None, env=["AAP_INTERNAL_URL"])
#     verify_ssl: bool = Field(False, env=["AAP_VALIDATE_CERTS", "CONTROLLER_VERIFY_SSL", "TOWER_VERIFY_SSL"])

#     @field_validator("internal_url", mode="before")
#     @classmethod
#     def ensure_scheme_and_validate(cls, v: Optional[str]) -> Optional[str]:
#         if v is None:
#             return v
#         if not v.startswith(("http://", "https://")):
#             v = f"https://{v}"
#         parsed = urlparse(v)
#         if not parsed.scheme or not parsed.netloc:
#             raise ValueError(f"Invalid controller host: {v!r}")
#         return v.rstrip("/")


# @lru_cache()
# def get_aap_settings() -> AAPSettings:
#     return AAPSettings()

from urllib.parse import urlparse

from dynaconf import Dynaconf

# Load defaults first, then override with .env or environment variables
settings = Dynaconf(
    settings_files=["settings/defaults.py", ".env"],  # defaults, then env overrides
    envvar_prefix="AAP",
    envvar_cast=True,
    load_dotenv=True,
)


def validate_url(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = f"http://{url}"
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL: {url}")
    return url.rstrip("/")


class AAPSettings:
    def __init__(self):
        raw_url = settings.get("URL")  # Changed from "INTERNAL_URL" to "URL"
        if not raw_url:
            raise ValueError("AAP_URL is required")
        self.url = validate_url(raw_url)

        self.verify_ssl = settings.get("VALIDATE_CERTS", False)

        self.username = settings.get("USERNAME")
        if not self.username:
            raise ValueError("AAP_USERNAME is required")

        self.password = settings.get("PASSWORD")
        if not self.password:
            raise ValueError("AAP_PASSWORD is required")


def get_aap_settings() -> AAPSettings:
    return AAPSettings()
