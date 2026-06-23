"""Cleanup policies for downloaded/extracted RF files."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Literal

CleanupMode = Literal["none", "extracted", "all_raw"]


def cleanup_raw_files(raw_month_dir: Path, mode: CleanupMode) -> None:
    raw_month_dir = Path(raw_month_dir)
    if mode == "none" or not raw_month_dir.exists():
        return
    if mode == "all_raw":
        shutil.rmtree(raw_month_dir)
        return
    if mode == "extracted":
        for csv_file in raw_month_dir.glob("*.csv"):
            csv_file.unlink()
        return
    raise ValueError("cleanup mode deve ser 'none', 'extracted' ou 'all_raw'.")
