"""Declarative base class that every ORM model will inherit from (starting in Stage 2)."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
