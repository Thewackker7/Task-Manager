# Import every model here so Alembic and SQLAlchemy "see" all tables via Base.metadata.
from app.models.user import User

__all__ = ["User"]
