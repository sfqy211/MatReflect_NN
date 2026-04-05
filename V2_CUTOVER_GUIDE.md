# V2 Cutover Guide

## Default Entry

V2 is now the primary UI entry for this repository. The old Streamlit app remains available as a fallback.

## Development Mode

Use the unified launcher:

```powershell
scripts\start_v2_dev.ps1
```

This starts:

- FastAPI backend on `http://127.0.0.1:8000`
- Vite frontend on `http://127.0.0.1:5173`

## Production Mode

Use the production launcher:

```powershell
scripts\start_v2_prod.ps1
```

This will:

1. Build `frontend/dist`
2. Start FastAPI
3. Serve the built V2 frontend directly from the backend root URL

Default URL:

- App: `http://127.0.0.1:8000`
- API docs: `http://127.0.0.1:8000/docs`

## Environment Notes

- Backend default env: `matreflect`
- `HyperBRDF` env: `hyperbrdf`
- `DecoupledHyperBRDF` env: `decoupledhyperbrdf`
- `HyperBRDF` and `DecoupledHyperBRDF` checkpoints are managed separately

## Fallback Entry

If you need the old Streamlit workflow, keep using:

```powershell
conda activate matreflect
streamlit run app.py
```
