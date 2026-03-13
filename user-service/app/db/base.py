"""SQLAlchemy declarative base."""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """All ORM models extend this base."""
    pass
