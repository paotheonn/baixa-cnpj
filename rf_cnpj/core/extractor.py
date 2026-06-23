"""Safe ZIP extraction for Receita Federal files."""

from __future__ import annotations

import zipfile
import shutil
from pathlib import Path

from .events import EventEmitter, emit_event


def _target_name(zip_path: Path, index: int, total: int) -> str:
    stem = zip_path.stem.lower()
    if total <= 1:
        return f"{stem}.csv"
    return f"{stem}_{index}.csv"


def _ensure_safe_member(destination: Path, member_name: str) -> Path:
    target = destination / member_name
    destination_resolved = destination.resolve()
    target_resolved = target.resolve()
    if not target_resolved.is_relative_to(destination_resolved):
        raise ValueError(f"unsafe ZIP member path: {member_name}")
    return target


def extract_zip_safely(zip_path: Path, destination: Path | None = None) -> list[Path]:
    zip_path = Path(zip_path)
    destination = Path(destination or zip_path.parent)
    destination.mkdir(parents=True, exist_ok=True)

    extracted: list[Path] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        members = [member for member in zf.namelist() if not member.endswith("/")]
        for member in members:
            _ensure_safe_member(destination, member)

        for index, member in enumerate(members):
            target = destination / _target_name(zip_path, index, len(members))
            with zf.open(member, "r") as source, open(target, "wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted.append(target)
    return extracted


class MonthExtractor:
    """Extracts all ZIP files for a downloaded RF month."""

    def __init__(self, emit: EventEmitter | None = None):
        self.emit = emit

    def extract_month(self, month_dir: Path, zip_files: list[Path] | None = None) -> list[Path]:
        extracted: list[Path] = []
        files = zip_files if zip_files is not None else sorted(Path(month_dir).glob("*.zip"))
        for zip_path in files:
            emit_event(self.emit, "extract_start", f"Extraindo {zip_path.name}", data={"filename": zip_path.name})
            try:
                extracted_files = extract_zip_safely(zip_path, month_dir)
            except Exception:
                emit_event(
                    self.emit,
                    "extract_error",
                    f"Erro ao extrair {zip_path.name}",
                    level="error",
                    data={"filename": zip_path.name},
                )
                raise
            extracted.extend(extracted_files)
            emit_event(
                self.emit,
                "extract_done",
                f"Extracao concluida: {zip_path.name}",
                level="success",
                data={"filename": zip_path.name, "extracted_files": [path.name for path in extracted_files]},
            )
        return extracted
