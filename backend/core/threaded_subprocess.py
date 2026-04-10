from __future__ import annotations

import asyncio
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping, Optional, Sequence


async def run_process_streaming(
    cmd: Sequence[str],
    *,
    cwd: Optional[Path] = None,
    env: Optional[Mapping[str, str]] = None,
    use_shell: bool = False,
    cancel_event: Optional[asyncio.Event] = None,
    process_store: Optional[dict[str, Any]] = None,
    process_key: Optional[str] = None,
    on_output: Optional[Callable[[bytes], Awaitable[None]]] = None,
) -> int:
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[tuple[str, Any]] = asyncio.Queue()
    popen_cmd: Any = subprocess.list2cmdline(list(cmd)) if use_shell else [str(part) for part in cmd]
    process = subprocess.Popen(
        popen_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        cwd=str(cwd) if cwd else None,
        env=dict(env) if env is not None else None,
        shell=use_shell,
    )

    if process_store is not None and process_key is not None:
        process_store[process_key] = process

    def enqueue(kind: str, payload: Any) -> None:
        loop.call_soon_threadsafe(queue.put_nowait, (kind, payload))

    def reader() -> None:
        try:
            if process.stdout is not None:
                while True:
                    line = process.stdout.readline()
                    if not line:
                        break
                    enqueue("line", line)
        except Exception as exc:
            enqueue("error", exc)
        finally:
            try:
                if process.stdout is not None:
                    process.stdout.close()
            except Exception:
                pass
            enqueue("done", process.wait())

    reader_thread = threading.Thread(target=reader, daemon=True)
    reader_thread.start()

    cancelled = False
    exit_code: Optional[int] = None
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set() and not cancelled:
                cancelled = True
                terminate_process(process)
            try:
                kind, payload = await asyncio.wait_for(queue.get(), timeout=0.2)
            except asyncio.TimeoutError:
                if process.poll() is not None and not reader_thread.is_alive():
                    exit_code = process.returncode
                    break
                continue
            if kind == "line":
                if on_output is not None:
                    await on_output(payload)
                continue
            if kind == "error":
                raise payload
            if kind == "done":
                exit_code = int(payload)
                break
        if cancelled:
            return -1
        return exit_code if exit_code is not None else int(process.returncode or 0)
    finally:
        if process.poll() is None:
            terminate_process(process)
        if process_store is not None and process_key is not None:
            process_store.pop(process_key, None)
        reader_thread.join(timeout=1.0)


def process_is_running(process: Any) -> bool:
    return process is not None and getattr(process, "poll", None) is not None and process.poll() is None


def terminate_process(process: Any, timeout: float = 3.0) -> None:
    if not process_is_running(process):
        return
    try:
        process.terminate()
    except Exception:
        return
    deadline = time.monotonic() + timeout
    while process.poll() is None and time.monotonic() < deadline:
        time.sleep(0.1)
    if process.poll() is None:
        try:
            process.kill()
        except Exception:
            pass
