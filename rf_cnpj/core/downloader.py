"""Receita Federal CNPJ downloader."""

from __future__ import annotations

from pathlib import Path
import zipfile

import requests

from .events import EventEmitter, emit_event, format_bytes
from .models import ProcessingOptions
from .schemas import DOWNLOAD_GROUP_FILES, REQUIRED_DOWNLOAD_GROUPS

NEXTCLOUD_SHARE_TOKEN = "YggdBLfdninEJX9"
NEXTCLOUD_WEBDAV_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav/"


def planned_download_files(options: ProcessingOptions) -> list[str]:
    groups = list(REQUIRED_DOWNLOAD_GROUPS)
    optional_flags = {
        "cnaes": options.include_cnaes,
        "simples": options.include_simples,
        "motivos": options.include_motivos,
        "naturezas": options.include_naturezas,
        "qualificacoes": options.include_qualificacoes,
        "paises": options.include_paises,
        "socios": options.include_socios,
    }
    groups.extend(group for group, enabled in optional_flags.items() if enabled)

    files: list[str] = []
    for group in groups:
        files.extend(DOWNLOAD_GROUP_FILES[group])
    return files


class DownloaderRF:
    """Downloads the ZIP files needed for one RF CNPJ month."""

    def __init__(self, data_dir: Path, session: requests.Session | None = None, emit: EventEmitter | None = None):
        self.data_dir = Path(data_dir)
        self.rf_dir = self.data_dir / "receita_federal"
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": "rf-cnpj/0.1"})
        self.emit = emit

    def month_dir(self, month: str) -> Path:
        return self.rf_dir / month

    def download_month(self, month: str, options: ProcessingOptions) -> list[Path]:
        month_dir = self.month_dir(month)
        month_dir.mkdir(parents=True, exist_ok=True)
        downloaded: list[Path] = []

        for filename in planned_download_files(options):
            downloaded.append(self.download_file(month, filename))
        return downloaded

    def download_file(self, month: str, filename: str) -> Path:
        month_dir = self.month_dir(month)
        month_dir.mkdir(parents=True, exist_ok=True)
        target = month_dir / filename
        if target.exists() and target.stat().st_size > 0:
            if zipfile.is_zipfile(target):
                emit_event(
                    self.emit,
                    "download_skip",
                    f"{filename} ja existe; pulando download",
                    data={"filename": filename, "path": target.as_posix(), "bytes": target.stat().st_size},
                )
                return target
            target.unlink()
        partial = target.with_name(f"{target.name}.part")

        url = f"{NEXTCLOUD_WEBDAV_URL}{month}/{filename}"
        try:
            emit_event(self.emit, "download_start", f"Baixando {filename}", data={"filename": filename, "url": url})
            with self.session.get(url, auth=(NEXTCLOUD_SHARE_TOKEN, ""), stream=True, timeout=120) as response:
                response.raise_for_status()
                total = None
                content_length = getattr(response, "headers", {}).get("content-length")
                if content_length:
                    total = int(content_length)
                downloaded = 0
                with open(partial, "wb") as f:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            total_text = f" de {format_bytes(total)}" if total is not None else ""
                            emit_event(
                                self.emit,
                                "download_progress",
                                f"Baixando {filename}: {format_bytes(downloaded)}{total_text}",
                                data={
                                    "filename": filename,
                                    "downloaded_bytes": downloaded,
                                    "total_bytes": total,
                                },
                            )
            if not zipfile.is_zipfile(partial):
                raise zipfile.BadZipFile(f"Downloaded file is not a valid ZIP: {filename}")
            partial.replace(target)
            emit_event(
                self.emit,
                "download_done",
                f"Download concluido: {filename} ({format_bytes(target.stat().st_size)})",
                level="success",
                data={"filename": filename, "path": target.as_posix(), "bytes": target.stat().st_size},
            )
        except Exception:
            emit_event(
                self.emit,
                "download_error",
                f"Erro ao baixar {filename}",
                level="error",
                data={"filename": filename},
            )
            if partial.exists():
                partial.unlink()
            if target.exists() and target.stat().st_size == 0:
                target.unlink()
            raise
        return target
