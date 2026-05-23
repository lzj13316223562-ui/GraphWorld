from __future__ import annotations


class GraphWorldAPIError(Exception):
    """Base exception for recoverable API-layer errors."""


class NotFoundError(GraphWorldAPIError):
    """Raised when a requested domain object does not exist."""


class InvalidStateError(GraphWorldAPIError):
    """Raised when a request does not match the current run state."""
