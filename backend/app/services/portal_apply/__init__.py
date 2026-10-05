"""Portal application adapters — Dice first, extensible registry for other portals."""

from app.services.portal_apply.base import (
    ApplicantPayload,
    ApplyResult,
    JobApplyTarget,
    PortalApplyAdapter,
    ProgressCallback,
)
from app.services.portal_apply.registry import resolve_adapter

__all__ = [
    "ApplicantPayload",
    "ApplyResult",
    "JobApplyTarget",
    "PortalApplyAdapter",
    "ProgressCallback",
    "resolve_adapter",
]
