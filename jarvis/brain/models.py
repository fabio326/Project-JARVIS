"""Structured planning models for the JARVIS brain layer."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """High-level action the orchestrator should take."""

    answer = "answer"
    use_tool = "use_tool"
    clarify = "clarify"
    refuse = "refuse"


class Plan(BaseModel):
    """A safe, structured plan produced by the planner agent."""

    action: ActionType
    reasoning_summary: str = Field(
        ...,
        description="Brief user-safe explanation of the chosen action.",
        max_length=200,
    )
    selected_skill: str | None = Field(
        default=None,
        description="Tool skill name when action is use_tool.",
    )
    requires_confirmation: bool = Field(
        default=False,
        description="True when the action is consequential.",
    )
    clarification_question: str | None = Field(
        default=None,
        description="Question to ask when action is clarify.",
    )
