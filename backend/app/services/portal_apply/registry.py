"""Adapter registry — supervised job-board apply for Dice, CareerBuilder, Monster, etc."""

from __future__ import annotations

from app.services.portal_apply.base import PortalApplyAdapter
from app.services.portal_apply.job_board import JobBoardApplyAdapter
from app.services.portal_apply.manual import ManualApplyAdapter

_ADAPTERS: list[PortalApplyAdapter] = [
    JobBoardApplyAdapter(),
]
_FALLBACK = ManualApplyAdapter()


def resolve_adapter(portal_name: str, posting_url: str) -> PortalApplyAdapter:
    for adapter in _ADAPTERS:
        if adapter.supports(portal_name or "", posting_url or ""):
            return adapter
    return _FALLBACK


def playwright_available() -> bool:
    try:
        import playwright  # noqa: F401

        return True
    except ImportError:
        return False
