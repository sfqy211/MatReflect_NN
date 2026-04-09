# Desktop Packaging

This project can be launched as a desktop application by embedding the existing V2 frontend in a `pywebview` window.

## What This Wrapper Does

- Reuses the current `React + FastAPI` V2 UI without rewriting frontend pages.
- Starts the FastAPI backend locally inside the desktop process.
- Opens a native desktop window instead of requiring a browser tab.

## What It Does Not Bundle

The desktop wrapper keeps using the current project workspace:

- `frontend/dist`
- `backend/`
- `scene/`
- `data/`
- local Mitsuba files
- local Conda environments used by training flows

This keeps the wrapper small and avoids repackaging large research assets.

## Runtime Requirements

- Windows desktop environment
- `matreflect` Conda environment
- `frontend/dist` already built
- WebView2 installed on Windows

## Quick Start

Run the desktop window directly from source:

```powershell
scripts\start_v2_desktop.ps1
```

Build the desktop executable:

```powershell
scripts\build_v2_desktop.ps1
```

The generated executable is intended to run inside the current project workspace. If you move it elsewhere, pass `--project-root` or set `MATREFLECT_PROJECT_ROOT`.
