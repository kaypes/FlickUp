import os
from gettext import gettext as _
from pathlib import Path

from gi.repository import GLib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

_SCOPES = ["https://www.googleapis.com/auth/drive.file"]

_CREDENTIALS = Path(
    os.environ.get(
        "FLICKUP_CREDENTIALS", Path(__file__).parent.parent / "credentials.json"
    )
)
_TOKEN = Path(
    os.environ.get(
        "FLICKUP_TOKEN", Path(GLib.get_user_config_dir()) / "flickup" / "token.json"
    )
)


def _get_credentials() -> Credentials:
    creds = None

    if _TOKEN.exists():
        creds = Credentials.from_authorized_user_file(str(_TOKEN), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not _CREDENTIALS.exists():
                raise FileNotFoundError(
                    _(
                        "credentials.json not found. Please set up Google Drive credentials."
                    )
                )
            flow = InstalledAppFlow.from_client_secrets_file(str(_CREDENTIALS), _SCOPES)
            creds = flow.run_local_server(port=0)

        _TOKEN.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN.write_text(creds.to_json())

    return creds


def _find_or_create_folder(service, name: str) -> str:
    safe = name.replace("'", "\\'")
    query = (
        f"name='{safe}' and "
        "mimeType='application/vnd.google-apps.folder' and "
        "trashed=false"
    )
    results = service.files().list(q=query, fields="files(id)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    metadata = {"name": name, "mimeType": "application/vnd.google-apps.folder"}
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder["id"]


def upload_sync(file_path: str, folder_name: str) -> None:
    """Blocking upload. Call from a background thread. Raises on error."""
    creds = _get_credentials()
    service = build("drive", "v3", credentials=creds)

    media = MediaFileUpload(file_path, resumable=True)
    metadata = {"name": Path(file_path).name}
    if folder_name:
        metadata["parents"] = [_find_or_create_folder(service, folder_name)]

    service.files().create(body=metadata, media_body=media, fields="id").execute()
