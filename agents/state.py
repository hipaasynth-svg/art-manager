"""
Local JSON persistence for the agent's business state.

This is the working copy on disk. Between runs it is made durable two ways
(either/both): the GitHub Actions job persists it to the ``studio-state`` branch
(see ``.github/workflows/daily.yml``), and, when a service account is set,
``agents/drive.py`` mirrors it to Google Drive. Locally, this keeps pieces,
pipeline, revenue, and learnings across runs instead of resetting each time.
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import AgentState


def save_state(state: AgentState, path: str) -> None:
    """Write the agent state to ``path`` as pretty-printed JSON."""
    p = Path(path)
    if p.parent and not p.parent.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(state.model_dump_json(indent=2), encoding="utf-8")


def load_state(path: str) -> AgentState:
    """Load agent state from ``path``.

    Returns a fresh, empty ``AgentState`` if the file does not exist yet, so
    first runs work without special-casing.
    """
    p = Path(path)
    if not p.exists():
        return AgentState()
    data = json.loads(p.read_text(encoding="utf-8"))
    return AgentState.model_validate(data)
