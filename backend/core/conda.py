from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def find_conda_command() -> str | None:
    candidates: list[str] = []

    def append_candidate(value: str | None) -> None:
        if not value:
            return
        text = value.strip()
        if not text or text in candidates:
            return
        candidates.append(text)

    append_candidate(os.environ.get("CONDA_EXE"))
    append_candidate(shutil.which("conda"))
    append_candidate(shutil.which("conda.bat"))

    home = Path.home()
    for root_name in ("miniconda3", "anaconda3", "miniforge3", "mambaforge"):
        append_candidate(str(home / root_name / "condabin" / "conda.bat"))
        append_candidate(str(home / root_name / "Scripts" / "conda.exe"))

    for candidate in candidates:
        if Path(candidate).exists():
            return str(Path(candidate))
    return None


def build_python_runner(conda_env: str | None = None) -> tuple[list[str], bool]:
    conda_cmd = find_conda_command()
    if conda_cmd and conda_env:
        use_shell = conda_cmd.lower().endswith((".bat", ".cmd"))
        return [conda_cmd, "run", "--no-capture-output", "-n", conda_env, "python"], use_shell
    return [sys.executable], False
