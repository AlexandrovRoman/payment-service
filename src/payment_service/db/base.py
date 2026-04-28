"""Declarative base for all ORM models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All ORM models inherit from this base.

    Centralizes metadata so Alembic can auto-detect models by importing
    the base (see alembic/env.py).
    """
