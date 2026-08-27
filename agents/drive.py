"""
Optional Google Drive persistence for agent state.

State still lives in a local JSON file (``agents/state.py``) as the working
copy; when Drive is configured this MIRRORS that JSON up to the configured Drive
folder after each save and restores it before load — so state survives a
machine that is wiped between runs (the container the agent runs in is
ephemeral).

Configuration (all optional — without it the agent just uses local disk):

    ART_MANAGER_DRIVE_CREDENTIALS=/path/to/service-account.json
    # or the standard GOOGLE_APPLICATION_CREDENTIALS
    ART_MANAGER_DRIVE_STATE_ID=<folder id>   # already defaulted in config.py

The service account must have access to the target Drive folder (share the
folder with the service account's email). Requires ``google-api-python-client``
and ``google-auth`` (see ``requirements-drive.txt``); both are imported lazily,
so the package still imports and its pure tests still pass without them.
"""

from __future__ import annotations

import os

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]
STATE_FILENAME = "art_manager_state.json"


def _credentials_path() -> str:
    return (
        os.environ.get("ART_MANAGER_DRIVE_CREDENTIALS")
        or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        or ""
    ).strip()


def drive_configured() -> bool:
    """True only when a credentials file exists AND the client libraries import."""
    path = _credentials_path()
    if not path or not os.path.exists(path):
        return False
    try:
        import googleapiclient  # noqa: F401
        import google.oauth2.service_account  # noqa: F401
    except ImportError:
        return False
    return True


def _service():
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    creds = service_account.Credentials.from_service_account_file(
        _credentials_path(), scopes=_SCOPES
    )
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _find_file_id(service, folder_id: str, filename: str) -> str | None:
    # Escape single quotes in the filename for the Drive query language.
    safe = filename.replace("'", "\\'")
    query = f"name = '{safe}' and '{folder_id}' in parents and trashed = false"
    resp = (
        service.files()
        .list(q=query, spaces="drive", fields="files(id, name)")
        .execute()
    )
    files = resp.get("files", [])
    return files[0]["id"] if files else None


def save_json(folder_id: str, filename: str, text: str) -> bool:
    """Upload or replace a JSON file in the folder. Returns True on success.

    Never raises — a Drive hiccup must not lose the run, and the local copy is
    always written first by the caller.
    """
    if not drive_configured() or not folder_id:
        return False
    try:
        from googleapiclient.http import MediaInMemoryUpload

        service = _service()
        media = MediaInMemoryUpload(text.encode("utf-8"), mimetype="application/json")
        existing = _find_file_id(service, folder_id, filename)
        if existing:
            service.files().update(fileId=existing, media_body=media).execute()
        else:
            service.files().create(
                body={"name": filename, "parents": [folder_id]},
                media_body=media,
                fields="id",
            ).execute()
        return True
    except Exception:  # noqa: BLE001 - Drive is best-effort; never break the run
        return False


def load_json(folder_id: str, filename: str) -> str | None:
    """Download a JSON file's text from the folder, or None if unavailable."""
    if not drive_configured() or not folder_id:
        return None
    try:
        service = _service()
        file_id = _find_file_id(service, folder_id, filename)
        if not file_id:
            return None
        data = service.files().get_media(fileId=file_id).execute()
        return data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data)
    except Exception:  # noqa: BLE001 - fall back to local state on any failure
        return None
