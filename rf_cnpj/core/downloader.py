"""Receita Federal CNPJ downloader."""

from __future__ import annotations

import os
from pathlib import Path
import zipfile

import requests

from .events import EventEmitter, emit_event, format_bytes
from .models import ProcessingOptions
from .schemas import DOWNLOAD_GROUP_FILES, REQUIRED_DOWNLOAD_GROUPS

DEFAULT_NEXTCLOUD_WEBDAV_URL = "https://arquivos.receitafederal.gov.br/public.php/webdav/"
SHARE_TOKEN_ENV = "RF_NEXTCLOUD_SHARE_TOKEN"
WEBDAV_URL_ENV = "RF_NEXTCLOUD_WEBDAV_URL"


def _dotenv_candidates() -> list[Path]:
    return [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]


def _apply_dotenv(path: Path) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return
    for raw_line in lines:
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        if value == "":
            continue
        os.environ[key] = value


def _load_local_dotenv() -> None:
    """Load a local .env without overriding variables already set in the environment."""
    seen: set[Path] = set()
    for path in _dotenv_candidates():
        try:
            resolved = path.resolve()
        except OSError:
            continue
        if resolved in seen or not path.is_file():
            continue
        seen.add(resolved)
        _apply_dotenv(path)


def nextcloud_share_token() -> str:
    """Public Receita Federal share id, read from the environment."""
    _load_local_dotenv()
    token = os.getenv(SHARE_TOKEN_ENV, "").strip()
    if not token:
        raise RuntimeError(
            "Defina RF_NEXTCLOUD_SHARE_TOKEN com o identificador publico do "
            "compartilhamento de dados abertos da Receita Federal. Veja .env.example."
        )
    return token


def nextcloud_webdav_url() -> str:
    _load_local_dotenv()
    configured = os.getenv(WEBDAV_URL_ENV, "").strip()
    base = configured or DEFAULT_NEXTCLOUD_WEBDAV_URL
    if not base.endswith("/"):
        base += "/"
    return base


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

        token = nextcloud_share_token()
        url = f"{nextcloud_webdav_url()}{month}/{filename}"
        try:
            emit_event(self.emit, "download_start", f"Baixando {filename}", data={"filename": filename, "url": url})
            with self.session.get(url, auth=(token, ""), stream=True, timeout=120) as response:
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
