import builtins
import subprocess
import sys

from rf_cnpj.core.file_dialog import pick_directory


def test_pick_directory_runs_tkinter_in_child_process_with_utf8_output(monkeypatch):
    calls = []

    def fail_if_parent_imports_tkinter(name, *args, **kwargs):
        if name == "tkinter" or name.startswith("tkinter."):
            raise AssertionError("tkinter must not run inside the API process")
        return real_import(name, *args, **kwargs)

    def fake_run(cmd, capture_output=False, text=False, check=False, encoding=None, env=None):
        calls.append((cmd, capture_output, text, check, encoding, env))

        class Result:
            returncode = 0
            stdout = "C:/bases/rf-cnpj\n"
            stderr = ""

        return Result()

    real_import = builtins.__import__
    monkeypatch.setattr(builtins, "__import__", fail_if_parent_imports_tkinter)
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert pick_directory("dados") == "C:/bases/rf-cnpj"
    cmd, capture_output, text, check, encoding, env = calls[0]
    assert cmd == [sys.executable, "-m", "rf_cnpj.core.file_dialog", "dados"]
    assert capture_output is True
    assert text is True
    assert check is False
    assert encoding == "utf-8"
    assert env["PYTHONIOENCODING"] == "utf-8"
