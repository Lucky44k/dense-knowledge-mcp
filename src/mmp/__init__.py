"""Model Module Protocol v1.0."""

from .errors import (
    ConflictNotice,
    DuplicateCandidates,
    MMPError,
    NotFoundError,
    ValidationError,
)
from .service import MMPStore

__all__ = [
    "ConflictNotice",
    "DuplicateCandidates",
    "MMPError",
    "MMPStore",
    "NotFoundError",
    "ValidationError",
]

__version__ = "1.1.1"
