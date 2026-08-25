"""
Configuration for the Art Manager, sourced from environment variables.

Every value has a default that preserves the project's current behaviour, so
nothing here is required to run locally. Override any of them via the
environment (see ``.env.example``) to point at a different site, model, or set
of Google Drive folders without editing code.

A local ``.env`` file at the project root is loaded automatically on import
(via python-dotenv), so keys like ANTHROPIC_API_KEY just work without any
manual ``export``. Real environment variables always win over ``.env``.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

# Default LLM used for creative / sales / agentic work.
DEFAULT_MODEL = "claude-opus-4-8"


def load_env(path: str | None = None) -> bool:
    """Load a ``.env`` file into the process environment.

    Uses python-dotenv if installed; a no-op (returns False) if it isn't, so the
    package still works without the dependency. Existing real environment
    variables are never overridden. With no ``path``, searches upward from the
    current directory for a ``.env``. Returns True if a file was loaded.
    """
    try:
        from dotenv import find_dotenv, load_dotenv
    except ImportError:
        return False
    dotenv_path = path or find_dotenv(usecwd=True)
    if not dotenv_path:
        return False
    return load_dotenv(dotenv_path, override=False)


# Auto-load .env on import so a project-root .env "just works".
load_env()


@dataclass(frozen=True)
class Config:
    # LLM
    model: str = DEFAULT_MODEL

    # Site ownership (changes shipped only via PR)
    github_owner: str = "hipaasynth-svg"
    github_repo: str = "codycarlson.art"
    default_branch: str = "main"
    site_url: str = "https://codycarlson.art"

    # Google Drive folder IDs
    drive_root_folder_id: str = "1uzI3VXasnvl-4_KemHN60dgwBP1_q4vr"
    drive_printouts_id: str = "1WUh8YNYO7736eUwhU0EctoM9wZWOHARM"
    drive_briefs_id: str = "1s3nujmMevAOGWvfCk-dwZf5l0SVuS2HB"
    drive_buyers_id: str = "103wQVeWOo-gVdeglZD_w7jwNbGsdnXJZ"
    drive_state_id: str = "1shpW9nOsr6EOHNblz23NUiZWIUucrlV4"

    # Local state persistence
    state_path: str = "art_manager_state.json"

    # Buyer search / enrichment (Google Places / Brave / SerpAPI / Apollo).
    # Empty = no real search wired; buyer leads stay AI-guessed.
    search_api_key: str = ""

    # Business targets
    monthly_revenue_goal: float = 2000.0


def _env(name: str, default: str) -> str:
    return os.environ.get(name, default)


def load_config() -> Config:
    """Build a Config, letting ART_MANAGER_* env vars override the defaults."""
    d = Config()
    return Config(
        model=_env("ART_MANAGER_MODEL", d.model),
        github_owner=_env("ART_MANAGER_GITHUB_OWNER", d.github_owner),
        github_repo=_env("ART_MANAGER_GITHUB_REPO", d.github_repo),
        default_branch=_env("ART_MANAGER_DEFAULT_BRANCH", d.default_branch),
        site_url=_env("ART_MANAGER_SITE_URL", d.site_url),
        drive_root_folder_id=_env("ART_MANAGER_DRIVE_ROOT_ID", d.drive_root_folder_id),
        drive_printouts_id=_env("ART_MANAGER_DRIVE_PRINTOUTS_ID", d.drive_printouts_id),
        drive_briefs_id=_env("ART_MANAGER_DRIVE_BRIEFS_ID", d.drive_briefs_id),
        drive_buyers_id=_env("ART_MANAGER_DRIVE_BUYERS_ID", d.drive_buyers_id),
        drive_state_id=_env("ART_MANAGER_DRIVE_STATE_ID", d.drive_state_id),
        state_path=_env("ART_MANAGER_STATE_PATH", d.state_path),
        search_api_key=_env("ART_MANAGER_SEARCH_API_KEY", d.search_api_key),
        monthly_revenue_goal=float(
            _env("ART_MANAGER_MONTHLY_REVENUE_GOAL", str(d.monthly_revenue_goal))
        ),
    )
