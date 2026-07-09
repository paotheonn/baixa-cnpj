"""Command line entry points for rf-cnpj."""

from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def _print_event(event: dict) -> None:
    timestamp = event.get("timestamp", "")
    time_part = timestamp[11:19] if len(timestamp) >= 19 else datetime.now().strftime("%H:%M:%S")
    level = str(event.get("level", "info")).upper()
    event_type = event.get("type", "")
    message = event.get("message", "")
    print(f"[{time_part}] [{level}] {event_type} - {message}", flush=True)


def _run_pipeline(args: argparse.Namespace) -> int:
    from .core.models import ProcessingOptions, RunConfig, Scope
    from .core.processor import PipelineRunner
    from .core.ui_options import (
        DEFAULT_TABLE_LABELS,
        build_output_name,
        options_from_labels,
    )

    if args.scope == "brasil":
        scope = Scope(type="brasil")
    else:
        scope = Scope(type=args.scope, uf=args.uf or "", municipio=args.municipio)

    tables = args.tables if args.tables is not None else DEFAULT_TABLE_LABELS
    options = options_from_labels(tables)

    output_name = args.output_name or build_output_name(
        month=args.month,
        uf=args.uf or "",
        municipio=args.municipio,
        scope_type=args.scope,
    )

    config = RunConfig(
        month=args.month,
        data_dir=Path(args.data_dir),
        output_dir=Path(args.output_dir),
        scope=scope,
        options=options,
        output_name=output_name,
        cleanup_mode=args.cleanup,
    )

    try:
        PipelineRunner().run(config, emit=_print_event)
    except Exception as exc:  # noqa: BLE001 - top-level CLI boundary
        print(f"[ERROR] pipeline falhou: {exc}", file=sys.stderr, flush=True)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rf-cnpj", description="Pipeline local para dados CNPJ da Receita Federal.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("web", help="abre a interface local Next.js/shadcn")
    api_parser = subparsers.add_parser("api", help="abre a API local FastAPI")
    api_parser.add_argument("--reload", action="store_true", help="reinicia a API ao alterar arquivos")

    run_parser = subparsers.add_parser("run", help="executa a pipeline em modo headless (batch)")
    run_parser.add_argument("--scope", choices=["brasil", "uf", "municipio"], default="brasil", help="escopo de processamento")
    run_parser.add_argument("--month", required=True, help="mes da base RF no formato AAAA-MM")
    run_parser.add_argument("--uf", default="", help="UF (obrigatoria para scope uf/municipio)")
    run_parser.add_argument("--municipio", default=None, help="municipio (obrigatorio para scope municipio)")
    run_parser.add_argument("--data-dir", default="dados", help="diretorio de dados brutos")
    run_parser.add_argument("--output-dir", default="saida", help="diretorio de saida")
    run_parser.add_argument("--tables", nargs="*", default=None, help="tabelas auxiliares (default: todas)")
    run_parser.add_argument("--cleanup", choices=["none", "extracted", "all_raw"], default="extracted", help="politica de limpeza dos brutos")
    run_parser.add_argument("--output-name", default=None, help="nome base do arquivo de saida")

    args = parser.parse_args(argv)
    if args.command == "web":
        web_dir = Path.cwd() / "web"
        npm = "npm.cmd" if sys.platform == "win32" else "npm"
        result = subprocess.run([npm, "--prefix", str(web_dir), "run", "dev"], check=False)
        return result.returncode
    if args.command == "api":
        cmd = [sys.executable, "-m", "uvicorn", "rf_cnpj.api.app:app"]
        if args.reload:
            cmd.append("--reload")
        result = subprocess.run(cmd, check=False)
        return result.returncode
    if args.command == "run":
        return _run_pipeline(args)

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
