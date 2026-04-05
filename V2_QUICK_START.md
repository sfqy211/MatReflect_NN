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

## Optional env

If backend is not running on the default address, create `frontend/.env.local`:

```bash
VITE_API_BASE=http://127.0.0.1:8000/api/v1
```

## Current scope

- New V2 shell supports light / dark theme switching.
- Three module entries are in place:
  - Render
  - Analysis
  - Models
- Backend summary and file-list APIs are already wired.
- Next step is extracting real render services from the old Streamlit flow.
