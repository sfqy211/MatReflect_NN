from __future__ import annotations

import argparse
import asyncio
import os
import socket
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path
from typing import Optional

import uvicorn


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18000
DEFAULT_TITLE = "MatReflect_NN Desktop"


def configure_windows_event_loop_policy() -> None:
    if hasattr(asyncio, "WindowsProactorEventLoopPolicy"):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch MatReflect_NN as a desktop app.")
    parser.add_argument("--project-root", default="", help="Project root containing backend/, frontend/, scene/.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Backend bind host.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="Preferred backend port.")
    parser.add_argument("--width", type=int, default=1600, help="Initial window width.")
    parser.add_argument("--height", type=int, default=1000, help="Initial window height.")
    parser.add_argument("--min-width", type=int, default=1280, help="Minimum window width.")
    parser.add_argument("--min-height", type=int, default=800, help="Minimum window height.")
    parser.add_argument("--title", default=DEFAULT_TITLE, help="Desktop window title.")
    parser.add_argument("--debug", action="store_true", help="Enable desktop debug mode.")
    return parser.parse_args()


def candidate_roots(start_dir: Path) -> list[Path]:
    return [start_dir, *start_dir.parents]


def looks_like_project_root(path: Path) -> bool:
    return (
        (path / "backend" / "main.py").is_file()
        and (path / "frontend").is_dir()
        and (path / "scene").is_dir()
    )


def resolve_project_root(explicit: str) -> Path:
    candidates: list[Path] = []
    if explicit.strip():
        candidates.append(Path(explicit).expanduser())

    env_root = os.environ.get("MATREFLECT_PROJECT_ROOT", "").strip()
    if env_root:
        candidates.append(Path(env_root).expanduser())

    if getattr(sys, "frozen", False):
        candidates.extend(candidate_roots(Path(sys.executable).resolve().parent))

    candidates.extend(candidate_roots(Path(__file__).resolve().parent))
    candidates.extend(candidate_roots(Path.cwd().resolve()))

    seen: set[Path] = set()
    for raw_path in candidates:
        path = raw_path.resolve()
        if path in seen:
            continue
        seen.add(path)
        if looks_like_project_root(path):
            return path
    raise FileNotFoundError(
        "Unable to locate project root. Pass --project-root or set MATREFLECT_PROJECT_ROOT."
    )


def ensure_frontend_dist(project_root: Path) -> None:
    dist_index = project_root / "frontend" / "dist" / "index.html"
    if not dist_index.exists():
        raise FileNotFoundError(
            f"Frontend dist not found: {dist_index}. Run `cd frontend && npm run build` first."
        )


def choose_port(host: str, preferred_port: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, preferred_port))
        except OSError:
            probe.bind((host, 0))
        return int(probe.getsockname()[1])


class DesktopServer(uvicorn.Server):
    def install_signal_handlers(self) -> None:
        return


class BackendThread(threading.Thread):
    def __init__(self, host: str, port: int) -> None:
        super().__init__(daemon=True)
        self.host = host
        self.port = port
        self.server: Optional[DesktopServer] = None
        self.error: Optional[BaseException] = None

    def run(self) -> None:
        try:
            from backend.main import app

            config = uvicorn.Config(
                app,
                host=self.host,
                port=self.port,
                log_level="info",
                access_log=False,
            )
            self.server = DesktopServer(config)
            self.server.run()
        except BaseException as exc:  # pragma: no cover
            self.error = exc

    def stop(self) -> None:
        if self.server is not None:
            self.server.should_exit = True


def wait_for_backend(backend: BackendThread, host: str, port: int, timeout: float = 60.0) -> None:
    url = f"http://{host}:{port}/api/v1/health"
    deadline = time.time() + timeout
    while time.time() < deadline:
        if backend.error is not None:
            raise RuntimeError("Backend thread failed before readiness check.") from backend.error
        try:
            with urllib.request.urlopen(url, timeout=1.0) as response:
                if response.status == 200:
                    return
        except (OSError, urllib.error.URLError):
            time.sleep(0.25)
    raise TimeoutError(f"Backend did not become ready within {timeout:.1f}s: {url}")


def configure_environment(project_root: Path) -> None:
    runtime_root = project_root / "backend" / "runtime"
    os.environ["MATREFLECT_PROJECT_ROOT"] = str(project_root)
    os.environ.setdefault("MATREFLECT_RUNTIME_ROOT", str(runtime_root))
    os.environ.setdefault("MATREFLECT_OUTPUTS_ROOT", str(project_root / "data" / "outputs"))
    project_root_str = str(project_root)
    if project_root_str not in sys.path:
        sys.path.insert(0, project_root_str)
    os.chdir(project_root)


def main() -> int:
    configure_windows_event_loop_policy()
    args = parse_args()
    project_root = resolve_project_root(args.project_root)
    ensure_frontend_dist(project_root)
    configure_environment(project_root)

    port = choose_port(args.host, args.port)
    backend = BackendThread(args.host, port)
    backend.start()
    wait_for_backend(backend, args.host, port)

    if backend.error is not None:
        raise RuntimeError("Backend thread exited early.") from backend.error

    import webview

    window = webview.create_window(
        args.title,
        url=f"http://{args.host}:{port}",
        width=args.width,
        height=args.height,
        min_size=(args.min_width, args.min_height),
    )
    window.events.closed += lambda: backend.stop()

    try:
        webview.start(debug=args.debug)
    finally:
        backend.stop()
        backend.join(timeout=5.0)
        if backend.error is not None:
            raise RuntimeError("Backend thread failed during desktop session.") from backend.error
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        traceback.print_exc()
        raise
