"""
Loader — Parquet / Google Drive
Responsável por persistir os Parquets gerados pelos extractors no Google Drive.
"""

import os
from pathlib import Path
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2 import service_account

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID")

BRONZE_PATH = Path(__file__).resolve().parents[2] / "data-lakehouse" / "bronze"


def _get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)


def upload_parquet(file_path: Path, service=None) -> str:
    """Faz upload de um arquivo Parquet para o Google Drive."""
    if service is None:
        service = _get_drive_service()

    file_metadata = {
        "name": file_path.name,
        "parents": [FOLDER_ID],
    }
    media = MediaFileUpload(str(file_path), mimetype="application/octet-stream")
    uploaded = service.files().create(
        body=file_metadata, media_body=media, fields="id"
    ).execute()
    print(f"[Drive] {file_path.name} → id={uploaded['id']}")
    return uploaded["id"]


def upload_all_raw() -> None:
    """Faz upload de todos os Parquets da camada raw para o Drive."""
    service = _get_drive_service()
    parquets = list(BRONZE_PATH.rglob("*.parquet"))
    if not parquets:
        print("[Drive] Nenhum Parquet encontrado para upload.")
        return
    for p in parquets:
        upload_parquet(p, service=service)
    print(f"[Drive] {len(parquets)} arquivo(s) enviados.")


if __name__ == "__main__":
    upload_all_raw()
