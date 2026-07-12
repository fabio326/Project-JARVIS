"""Coordinates planning and the main JARVIS agent."""

from __future__ import annotations

import logging

from agents import Agent, Runner, SQLiteSession

from jarvis.brain.models import ActionType, Plan

logger = logging.getLogger(__name__)


class JarvisOrchestrator:
    """Run the planner first, then route to JARVIS or return a direct response."""

    def __init__(self, jarvis_agent: Agent, planner_agent: Agent) -> None:
        self.jarvis_agent = jarvis_agent
        self.planner_agent = planner_agent

    async def run(self, message: str, session: SQLiteSession) -> str:
        """Plan the request, then execute or respond safely."""
        try:
            plan = await self._plan(message)
        except Exception:
            logger.warning("Planner failed; falling back to JARVIS agent.")
            return await self._run_jarvis(message, session)

        logger.info(
            "Planner action=%s skill=%s confirmation=%s",
            plan.action.value,
            plan.selected_skill,
            plan.requires_confirmation,
        )

        if plan.action in {ActionType.answer, ActionType.use_tool}:
            return await self._run_jarvis(message, session)

        if plan.action == ActionType.clarify:
            return plan.clarification_question or plan.reasoning_summary

        if plan.action == ActionType.refuse:
            return plan.reasoning_summary

        return await self._run_jarvis(message, session)

    async def _plan(self, message: str) -> Plan:
        """Ask the planner for a structured Plan without using session memory."""
        result = await Runner.run(self.planner_agent, message)
        plan = result.final_output

        if not isinstance(plan, Plan):
            raise TypeError("Planner returned an invalid plan type.")

        return plan

    async def _run_jarvis(self, message: str, session: SQLiteSession) -> str:
        """Run the main JARVIS agent with persistent session memory."""
        result = await Runner.run(self.jarvis_agent, message, session=session)
        return str(result.final_output or "")
