# Local Data Science Agent

This repository contains a local, single-user, hybrid data science agent workspace.

## Backend Development

Create the backend environment:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\python -m pip install -e ".[dev]"
```

Run tests:

```powershell
cd backend
.\.venv\Scripts\python -m pytest -q
```

Run the API server:

```powershell
cd backend
.\.venv\Scripts\python -m uvicorn app.main:app --reload --port 8000
```

The health endpoint is available at:

```text
http://127.0.0.1:8000/health
```
