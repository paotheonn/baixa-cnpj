"""Output writers for processed CNPJ data."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from .models import ExportResult
from .normalization import safe_filename


def export_csv_and_parquet(df: pd.DataFrame, output_dir: Path, base_name: str) -> ExportResult:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_base = safe_filename(base_name)
    csv_path = output_dir / f"{safe_base}.csv"
    parquet_path = output_dir / f"{safe_base}.parquet"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_parquet(parquet_path, index=False)

    return ExportResult(csv_path=csv_path, parquet_path=parquet_path, rows=len(df))


class IncrementalUFExporter:
    """Writes per-UF result parts with a checkpoint manifest, then merges into
    single CSV/Parquet files.

    Layout under ``output_dir``:
      - ``<base>.parts/<UF>.csv`` and ``<base>.parts/<UF>.parquet`` per finished UF
      - ``<base>.manifest.json`` checkpoint listing finished UFs
      - ``<base>.csv`` and ``<base>.parquet`` final merged outputs
    """

    def __init__(self, output_dir: Path, base_name: str):
        self.output_dir = Path(output_dir)
        self.base_name = safe_filename(base_name)
        self.parts_dir = self.output_dir / f"{self.base_name}.parts"
        self.manifest_path = self.output_dir / f"{self.base_name}.manifest.json"
        self.csv_path = self.output_dir / f"{self.base_name}.csv"
        self.parquet_path = self.output_dir / f"{self.base_name}.parquet"

    def _part_paths(self, uf: str) -> tuple[Path, Path]:
        uf = uf.upper().strip()
        return self.parts_dir / f"{uf}.csv", self.parts_dir / f"{uf}.parquet"

    def _read_manifest(self) -> dict:
        if not self.manifest_path.exists():
            return {}
        try:
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}

    def _write_manifest(self, manifest: dict) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.manifest_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(self.manifest_path)

    def completed_ufs(self) -> set[str]:
        manifest = self._read_manifest()
        return {uf.upper() for uf in manifest.get("ufs", {})}

    def write_uf(self, uf: str, df: pd.DataFrame) -> None:
        """Persist one UF's data to temporary parts, then record it in the manifest.

        The manifest is only updated after both files are fully written, so a crash
        mid-write leaves the UF unrecorded and it will be reprocessed on resume.
        """
        uf = uf.upper().strip()
        self.parts_dir.mkdir(parents=True, exist_ok=True)
        csv_part, parquet_part = self._part_paths(uf)

        csv_tmp = csv_part.with_suffix(".csv.tmp")
        parquet_tmp = parquet_part.with_suffix(".parquet.tmp")
        df.to_csv(csv_tmp, index=False, encoding="utf-8-sig")
        df.to_parquet(parquet_tmp, index=False)
        csv_tmp.replace(csv_part)
        parquet_tmp.replace(parquet_part)

        manifest = self._read_manifest()
        ufs = manifest.get("ufs", {})
        ufs[uf] = {"rows": int(len(df))}
        manifest.update({
            "base_name": self.base_name,
            "status": "in_progress",
            "ufs": ufs,
        })
        self._write_manifest(manifest)

    def merge(self) -> ExportResult:
        """Concatenate all UF parts (in sorted UF order) into single outputs."""
        ufs = sorted(self.completed_ufs())
        self.output_dir.mkdir(parents=True, exist_ok=True)

        total_rows = 0
        writer: pq.ParquetWriter | None = None
        wrote_csv_header = False

        # Fresh outputs.
        if self.csv_path.exists():
            self.csv_path.unlink()

        try:
            for uf in ufs:
                csv_part, parquet_part = self._part_paths(uf)
                if not parquet_part.exists():
                    continue
                table = pq.read_table(parquet_part)
                if writer is None:
                    writer = pq.ParquetWriter(self.parquet_path, table.schema)
                else:
                    table = table.cast(writer.schema)
                writer.write_table(table)

                part_df = table.to_pandas()
                part_df.to_csv(
                    self.csv_path,
                    index=False,
                    encoding="utf-8-sig",
                    mode="a",
                    header=not wrote_csv_header,
                )
                wrote_csv_header = True
                total_rows += len(part_df)
        finally:
            if writer is not None:
                writer.close()

        if writer is None:
            # No parts at all: emit empty outputs so downstream contracts hold.
            empty = pa.table({})
            pq.write_table(empty, self.parquet_path)
            self.csv_path.write_text("", encoding="utf-8-sig")

        manifest = self._read_manifest()
        manifest["status"] = "done"
        self._write_manifest(manifest)

        return ExportResult(csv_path=self.csv_path, parquet_path=self.parquet_path, rows=total_rows)

    def cleanup(self) -> None:
        """Remove temporary parts and the manifest after a successful merge."""
        if self.parts_dir.exists():
            shutil.rmtree(self.parts_dir, ignore_errors=True)
        if self.manifest_path.exists():
            self.manifest_path.unlink()
