"""Runtime path configuration for ajoa-kit.

Centralises the two path roots that the pipeline modules previously derived
from ``ROOT = Path(__file__).resolve().parents[2]``.  Resolving from CWD
(or from environment overrides) instead of ``__file__`` means the package
works correctly when installed as a wheel and in any working directory.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Runtime path configuration for ajoa-kit (pydantic-settings v2).

    All paths resolve from CWD (or from environment overrides), never from
    ``__file__``, so the package works correctly when installed as a wheel.

    Usage (call-site, inside the function that needs paths)::

        from ajoa_kit.settings import AppSettings
        settings = AppSettings()
    """

    model_config = SettingsConfigDict(
        env_prefix="AJOA_",
        env_file=".env",
        extra="ignore",
    )

    config_dir: Path = Field(
        default=Path("config"),
        description="Directory containing seed.json and seed-candidates.json.",
    )
    results_dir: Path = Field(
        default=Path("results"),
        description="Directory where ingest/chunk/persist artifacts are written.",
    )
    public_data_dir: Path = Field(
        default=Path("public-data"),
        description="PII-free publishable aggregates (trends); never PII, unlike results_dir.",
    )
