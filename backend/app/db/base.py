from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """
    SQLAlchemy Base class for declarative mapping.
    Uses SQLAlchemy 2.0 type mapping capabilities.
    """
    pass


# Ensure all declarative models are registered in the SQLAlchemy registry
import app.auth.models  # noqa: F401
import app.organizations.models  # noqa: F401
import app.investigations.models  # noqa: F401
import app.integrations.models  # noqa: F401

