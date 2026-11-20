# Task Manager API

Production-oriented task management backend built with FastAPI, PostgreSQL and SQLAlchemy.

## Run with Docker
```bash
cp .env.example .env          # Windows: copy .env.example .env
# Edit .env and set SECRET_KEY (see the comment inside the file)
docker compose up --build
```
- API docs: http://localhost:8000/docs  (use the **Authorize** button to log in)
- Health check: http://localhost:8000/api/v1/health

Migrations are applied automatically when the `api` container starts.

## Authentication
| Endpoint | Purpose |
|---|---|
| `POST /api/v1/auth/register` | JSON `{email, password, full_name?}` -> creates the account |
| `POST /api/v1/auth/login` | Form fields `username` (your email) + `password` -> `{access_token}` |
| `GET /api/v1/users/me` | Needs header `Authorization: Bearer <access_token>` |

## Run tests and lint locally
Tests need PostgreSQL running (`docker compose up -d db`).
```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
pytest
ruff check . && ruff format --check .
```

## Database migrations
```bash
alembic upgrade head                              # apply migrations
alembic revision --autogenerate -m "describe change"   # after changing a model
alembic downgrade -1                              # undo the last migration
```

## Status
- Stage 1: foundation (done)
- Stage 2: users and authentication (done)
