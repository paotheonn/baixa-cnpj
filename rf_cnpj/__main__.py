"""Module entrypoint for `python -m rf_cnpj`."""

from __future__ import annotations

from .cli import main


if __name__ == "__main__":
    raise SystemExit(main())
