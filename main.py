"""Terminal entry point for Project JARVIS."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from agents import Runner, SQLiteSession

from jarvis.agent import create_jarvis_agent

PROJECT_ROOT = Path(__file__).resolve().parent
MEMORY_DB = PROJECT_ROOT / "jarvis_memory.db"
SESSION_ID = "jarvis-terminal"


def load_api_key() -> str:
    """Load the OpenAI API key from the local .env file."""
    load_dotenv(PROJECT_ROOT / ".env")
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is missing from .env")
    os.environ["OPENAI_API_KEY"] = api_key
    return api_key


async def chat_loop() -> None:
    """Run the interactive JARVIS terminal session."""
    agent = create_jarvis_agent()
    session = SQLiteSession(SESSION_ID, MEMORY_DB)

    print("JARVIS is online.")
    print("Type your message, or 'exit' / 'quit' to end the session.\n")

    try:
        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGoodbye.")
                break

            if not user_input:
                continue
            if user_input.lower() in {"exit", "quit"}:
                print("Goodbye.")
                break

            result = await Runner.run(agent, user_input, session=session)
            print(f"JARVIS: {result.final_output}\n")
    finally:
        session.close()


def main() -> None:
    try:
        load_api_key()
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)

    try:
        asyncio.run(chat_loop())
    except KeyboardInterrupt:
        print("\nGoodbye.")


if __name__ == "__main__":
    main()
