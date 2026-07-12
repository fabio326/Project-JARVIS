"""Tests for brain planning models."""

import pytest
from pydantic import ValidationError

from jarvis.brain.models import ActionType, Plan


def test_action_type_values() -> None:
    assert ActionType.answer.value == "answer"
    assert ActionType.use_tool.value == "use_tool"
    assert ActionType.clarify.value == "clarify"
    assert ActionType.refuse.value == "refuse"


def test_plan_answer_validation() -> None:
    plan = Plan(
        action=ActionType.answer,
        reasoning_summary="General conversation request.",
        requires_confirmation=False,
    )
    assert plan.selected_skill is None
    assert plan.clarification_question is None


def test_plan_tool_validation() -> None:
    plan = Plan(
        action=ActionType.use_tool,
        reasoning_summary="Open Safari for the user.",
        selected_skill="open_application",
        requires_confirmation=True,
    )
    assert plan.selected_skill == "open_application"
    assert plan.requires_confirmation is True


def test_plan_clarification_validation() -> None:
    plan = Plan(
        action=ActionType.clarify,
        reasoning_summary="Need the target application.",
        clarification_question="Which app would you like me to open?",
        requires_confirmation=False,
    )
    assert plan.clarification_question is not None


def test_plan_requires_reasoning_summary() -> None:
    with pytest.raises(ValidationError):
        Plan(action=ActionType.refuse, requires_confirmation=False)
