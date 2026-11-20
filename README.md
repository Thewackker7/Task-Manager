# Task Manager API

Production-oriented task management backend built with FastAPI, PostgreSQL and SQLAlchemy.

## Run with Docker
```bash
cp .env.example .env
docker compose up --build
```
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/api/v1/health

## Run tests and lint locally
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

## Status
Stage 1 (foundation) complete. See the project roadmap for upcoming stages.
