"""Planner agent that inspects requests and returns a structured Plan."""

from __future__ import annotations

from agents import Agent

from jarvis.brain.models import Plan
from jarvis.tools.mac_tools import list_approved_applications

PLANNER_INSTRUCTIONS = f"""You are the JARVIS planning layer.

Your job is to inspect the user's request and return a structured Plan.
You do NOT execute tools and you do NOT claim any action already happened.

Available skills:
- open_application: open an approved Mac app
- open_website: open an allowed http/https website

Approved application aliases: {list_approved_applications()}.

Choose the action:
- answer: general conversation, questions, or help that needs no tool
- use_tool: the request clearly needs one existing skill
- clarify: the request is ambiguous and you need one short follow-up question
- refuse: the request is unsafe, unsupported, or outside current capabilities

Rules:
- reasoning_summary must be brief, user-safe, and contain no hidden chain-of-thought
- selected_skill must be null unless action is use_tool
- clarification_question must be null unless action is clarify
- Mark requires_confirmation true for consequential tool actions such as opening apps or websites
- Never invent skills beyond open_application and open_website
"""


def create_planner_agent() -> Agent:
    """Create the planner agent with structured Plan output."""
    return Agent(
        name="JARVIS Planner",
        instructions=PLANNER_INSTRUCTIONS,
        output_type=Plan,
    )
