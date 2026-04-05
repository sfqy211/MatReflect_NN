# V2 Quick Start

## Backend

```powershell
pip install -r backend/requirements.txt
python -m uvicorn backend.main:app --reload
```

Backend default:

- API: `http://127.0.0.1:8000/api/v1`
- Docs: `http://127.0.0.1:8000/docs`

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

Frontend default:

- App: `http://127.0.0.1:5173`

## Unified Launchers

Recommended entrypoints:

```powershell
scripts\start_v2_dev.ps1
scripts\start_v2_prod.ps1
```

Notes:

- `start_v2_dev.ps1` starts backend and Vite dev server in separate PowerShell windows
- `start_v2_prod.ps1` builds `frontend/dist` and serves V2 from the FastAPI root URL

## Optional env

If backend is not running on the default address, create `frontend/.env.local`:

```bash
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## Training envs

- `HyperBRDF` uses conda env `hyperbrdf`
- `DecoupledHyperBRDF` uses conda env `decoupledhyperbrdf`
- `Neural-BRDF` training can continue to use the existing Python environment or its dedicated env

Notes:

- `HyperBRDF` and `DecoupledHyperBRDF` checkpoints are managed separately.
- Do not assume a `HyperBRDF` `.pt` checkpoint can be used directly by `DecoupledHyperBRDF`.

## Current scope

- New V2 workspace supports light / dark theme switching.
- Core module entries are in place:
  - Render
  - Analysis
  - Models
- Settings page is also available for theme and system information.
- Backend summary and file-list APIs are already wired.
- V2 is now the primary entry; V1 Streamlit remains only as a fallback for legacy panels.
