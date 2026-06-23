"""Command line entry points for rf-cnpj."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="rf-cnpj", description="Pipeline local para dados CNPJ da Receita Federal.")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("web", help="abre a interface local Next.js/shadcn")
    api_parser = subparsers.add_parser("api", help="abre a API local FastAPI")
    api_parser.add_argument("--reload", action="store_true", help="reinicia a API ao alterar arquivos")

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

    parser.print_help()
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
