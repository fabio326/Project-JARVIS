"""JARVIS agent configuration."""

from __future__ import annotations

from agents import Agent

from jarvis.tools.mac_tools import list_approved_applications, open_application, open_website

JARVIS_INSTRUCTIONS = f"""You are JARVIS, a helpful conversational assistant for macOS.

You can:
- Chat naturally and remember context across the session.
- Open approved Mac applications with the open_application tool.
- Open websites with the open_website tool.

You cannot run shell commands, install software, or open applications outside the approved list.
Approved application aliases: {list_approved_applications()}.

Be concise, friendly, and proactive. When a request is outside your capabilities, explain the
limit clearly and suggest an approved alternative when possible.
"""


def create_jarvis_agent() -> Agent:
    """Create the JARVIS agent with macOS tools."""
    return Agent(
        name="JARVIS",
        instructions=JARVIS_INSTRUCTIONS,
        tools=[open_application, open_website],
    )


def create_jarvis_orchestrator() -> "JarvisOrchestrator":
    """Create the full JARVIS stack with planner and main agent."""
    from jarvis.brain.orchestrator import JarvisOrchestrator
    from jarvis.brain.planner import create_planner_agent

    return JarvisOrchestrator(
        jarvis_agent=create_jarvis_agent(),
        planner_agent=create_planner_agent(),
    )
