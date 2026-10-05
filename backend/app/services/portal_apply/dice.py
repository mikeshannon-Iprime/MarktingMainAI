"""Backward-compatible Dice exports — implementation lives in job_board.py."""

from app.services.portal_apply.job_board import (  # noqa: F401
    DiceApplyAdapter,
    JobBoardApplyAdapter,
    is_dice_target,
    is_job_board_target,
)

__all__ = [
    "DiceApplyAdapter",
    "JobBoardApplyAdapter",
    "is_dice_target",
    "is_job_board_target",
]
