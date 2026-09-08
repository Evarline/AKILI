"""Declarative base for AKILI's ORM models.

There are no models yet. They arrive in a later phase, and must follow
docs/01-AGENT-CONTRACT.md. Every model module will subclass `Base` here, and
must be imported by Alembic's env.py so autogenerate can see it.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all AKILI ORM models (SQLAlchemy 2.x style)."""
