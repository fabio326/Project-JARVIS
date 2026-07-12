"""Safe macOS tools for opening approved applications and websites."""

from __future__ import annotations

import subprocess
from urllib.parse import urlparse

from agents import function_tool

# Friendly aliases map to the exact macOS application name used by `open -a`.
APPROVED_APPLICATIONS: dict[str, str] = {
    "calendar": "Calendar",
    "chrome": "Google Chrome",
    "finder": "Finder",
    "mail": "Mail",
    "maps": "Maps",
    "messages": "Messages",
    "music": "Music",
    "notes": "Notes",
    "photos": "Photos",
    "preview": "Preview",
    "reminders": "Reminders",
    "safari": "Safari",
    "settings": "System Settings",
    "spotify": "Spotify",
    "terminal": "Terminal",
    "textedit": "TextEdit",
    "vscode": "Visual Studio Code",
}


def _normalize_app_name(app_name: str) -> str:
    return app_name.strip().lower().replace(".app", "")


def _resolve_application(app_name: str) -> str | None:
    key = _normalize_app_name(app_name)
    if key in APPROVED_APPLICATIONS:
        return APPROVED_APPLICATIONS[key]

    for alias, display_name in APPROVED_APPLICATIONS.items():
        if key == display_name.lower():
            return display_name

    return None


def _is_allowed_url(url: str) -> bool:
    parsed = urlparse(url.strip())
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def list_approved_applications() -> str:
    """Return a comma-separated list of approved application aliases."""
    return ", ".join(sorted(APPROVED_APPLICATIONS))


@function_tool
def open_application(app_name: str) -> str:
    """Open an approved Mac application.

    Args:
        app_name: The application to open. Use a friendly alias such as safari, chrome,
            terminal, notes, or spotify.
    """
    resolved = _resolve_application(app_name)
    if resolved is None:
        approved = list_approved_applications()
        return (
            f"'{app_name}' is not an approved application. "
            f"Approved apps: {approved}."
        )

    try:
        subprocess.run(
            ["open", "-a", resolved],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        return f"Failed to open {resolved}: {stderr}"

    return f"Opened {resolved}."


@function_tool
def open_website(url: str) -> str:
    """Open a website in the default browser.

    Args:
        url: A full website URL starting with http:// or https://.
    """
    normalized_url = url.strip()
    if not _is_allowed_url(normalized_url):
        return "Only http:// and https:// URLs are allowed."

    try:
        subprocess.run(
            ["open", normalized_url],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip() if exc.stderr else "unknown error"
        return f"Failed to open {normalized_url}: {stderr}"

    return f"Opened {normalized_url}."
