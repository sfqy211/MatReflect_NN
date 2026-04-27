# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MatReflect_NN is a Windows local material research workbench for BRDF (Bidirectional Reflectance Distribution Function) materials. It uses a V2 architecture with:
- Frontend: React + Vite
- Backend: FastAPI + WebSocket
- Training & Inference: Multi-environment Conda scheduling

Main workflows:
1. Render MERL `.binary` / NBRDF `.npy` / FullBin `.fullbin` materials using Mitsuba 0.6
2. Convert `.binary → .npy` via Neural-BRDF
3. Train and decode via HyperBRDF (`.binary → checkpoint.pt → .pt → .fullbin`)
4. Analyze render results (preview, PSNR/SSIM/Delta E evaluation, mosaic comparison)

## Commands

### Start Application
```powershell
# Development mode (opens two windows for frontend and backend)
scripts\start_v2_dev.ps1

# Production mode
scripts\start_v2_prod.ps1
```

### Backend
```powershell
# Activate environment and run backend
conda activate matreflect
python -m backend.run_server --reload --host 127.0.0.1 --port 8000

# Verify backend imports
python -c "import backend.main"
```

### Frontend
```powershell
cd frontend
npm install
npm run dev           # Development server
npm run build         # Production build (tsc && vite build)
frontend\node_modules\.bin\tsc.cmd --noEmit  # Type check only
```

## Conda Environments

| Environment | Purpose |
|-------------|---------|
| `matreflect` | V2 backend, rendering, analysis |
| `mitsuba-build` | Mitsuba 0.6 compilation (Python 2.7 + SCons) |
| `nbrdf-train` | Neural-BRDF training and H5→NPY conversion |
| `hyperbrdf` | HyperBRDF training, extraction, decoding |

Create `matreflect` environment:
```powershell
conda create -n matreflect -c conda-forge python=3.9 mamba -y
conda activate matreflect
mamba install -c conda-forge pyexr -y
pip install -r requirements.txt
pip install -r backend/requirements.txt
```

## Architecture

### Backend Structure
- `backend/main.py` — FastAPI app entry point, mounts API routers and static files
- `backend/run_server.py` — Windows-safe launcher (sets `ProactorEventLoopPolicy`)
- `backend/api/v1/` — API route handlers (render, train, analysis, system, fs)
- `backend/services/` — Business logic layer (render_service, train_service, analysis_service, system_service, task_manager, model_registry)
- `backend/core/` — Utilities (paths, config, system_settings, conda, websocket)
- `backend/runtime/` — Persistent state (tasks/, logs/, render_xml/, system_settings.json)

### Frontend Structure
- `frontend/src/App.tsx` — Root component with module routing
- `frontend/src/components/` — UI components (RenderWorkbench, AnalysisWorkbench, ModelsWorkbench, SettingsWorkbench)
- `frontend/src/features/` — State management hooks (use*Workbench.ts)
- `frontend/src/lib/fileNames.ts` — Output filename parsing utilities
- `frontend/src/types/api.ts` — API type definitions

### Key Files
| Area | File |
|------|------|
| Render service | `backend/services/render_service.py` |
| Train service | `backend/services/train_service.py` |
| Analysis service | `backend/services/analysis_service.py` |
| Model registry | `backend/services/model_registry.py` |
| Task management | `backend/services/task_manager.py` |
| Path resolution | `backend/core/paths.py` |
| Subprocess wrapper | `backend/core/threaded_subprocess.py` |
| System settings | `backend/core/system_settings.py` |

## Key Constraints

1. **Subprocess handling**: Always use `run_process_streaming` from `backend/core/threaded_subprocess.py`. Do NOT use `asyncio.create_subprocess_*` directly — Windows + Uvicorn reload + asyncio subprocess has compatibility issues.

2. **Path handling**: Use `pathlib.Path` everywhere. Paths should be constrained within `PROJECT_ROOT`. Use `resolve_workspace_path` from `file_service.py` for file browsing.

3. **Task persistence**: Tasks are stored in `backend/runtime/tasks/*.json`. On service restart, pending/running tasks are automatically marked as failed.

4. **WebSocket management**: Use `websocket_hub` from `backend/core/websocket.py` for WebSocket connections.

5. **Documentation vs code**: When documentation and code conflict, trust the code.

## Areas to Avoid Major Changes

- `mitsuba/src/` and `mitsuba/dist/` — Local Mitsuba build
- `Neural-BRDF/` — Upstream Neural-BRDF code
- `HyperBRDF/` — Upstream HyperBRDF code

## Naming Conventions

Output files: `{material_name}_{YYYYMMDD}_{HHMMSS}`

When changing naming rules, check all of:
- `backend/services/render_service.py` (generation)
- `frontend/src/lib/fileNames.ts` (parsing)
- `backend/services/analysis_service.py` (`normalize_material_name` function)

## Data Directories (gitignored)

- `scene/assets/` — Mitsuba scene assets (each scene in a subdirectory with `scene.xml`)
- `references/` — Read-only reference area
- `data/inputs/binary/` — MERL `.binary` files
- `data/inputs/npy/` — Neural-BRDF `.npy` weights
- `data/inputs/fullbin/` — FullBin `.fullbin` files
- `data/outputs/` — Render results (exr/png), grids, comparisons
- `backend/runtime/` — Tasks, logs, temporary XML files
- `mitsuba/dist/` — Built Mitsuba executable
