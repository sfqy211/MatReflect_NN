from __future__ import annotations

import logging
import subprocess
import sys
from pathlib import Path
from typing import Iterable


LOGGER_NAME = "matreflect.runtime"


def configure_runtime_logging() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    logger.propagate = False

    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(logging.INFO)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    logger.addHandler(handler)
    return logger


def get_runtime_logger() -> logging.Logger:
    return configure_runtime_logging()


def log_runtime(message: str, *, level: int = logging.INFO) -> None:
    get_runtime_logger().log(level, message)


def log_task_message(scope: str, task_id: str, message: str) -> None:
    log_runtime(f"[{scope}] [{task_id}] {message}")


def format_command(cmd: Iterable[str], *, cwd: Path, use_shell: bool) -> str:
    command = subprocess.list2cmdline(list(cmd))
    return f"[debug] cwd={cwd} | shell={use_shell} | cmd={command}"
