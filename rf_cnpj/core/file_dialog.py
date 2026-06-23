"""Native OS dialogs used by the local API."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def pick_directory(initial_dir: str | None = None) -> str | None:
    """Open a native directory picker in a child process.

    Tkinter must not run inside FastAPI/Uvicorn's worker thread. Running the
    dialog in a short-lived subprocess keeps Tcl/Tk lifecycle isolated.
    """
    cmd = [sys.executable, "-m", "rf_cnpj.core.file_dialog"]
    if initial_dir:
        cmd.append(initial_dir)

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        encoding="utf-8",
        env={**os.environ, "PYTHONIOENCODING": "utf-8"},
    )
    if result.returncode != 0:
        message = result.stderr.strip() or "Falha ao selecionar pasta"
        raise RuntimeError(message)
    path = result.stdout.strip()
    return path or None


def _pick_directory_with_tk(initial_dir: str | None = None) -> str | None:
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        path = filedialog.askdirectory(initialdir=initial_dir or str(Path.cwd()))
        return path or None
    finally:
        root.destroy()


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    selected = _pick_directory_with_tk(args[0] if args else None)
    if selected:
        print(selected)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
