from typing import Iterable, Sequence

from flask import current_app

CommandPath = Sequence[str]


def configure_set(commands: Iterable[CommandPath], error_context: str = "operation"):
    """Execute configure_set with error handling."""
    commands = list(commands)
    if not commands:
        return True, None

    response = current_app.device.configure_set(path=commands)
    if getattr(response, "error", None):
        return False, f"Failed to apply configuration for {error_context}: {response.error}"
    if getattr(response, "status", 200) != 200:
        return False, f"Device returned status {response.status} for {error_context}"
    return True, None


def configure_delete(paths: Iterable[CommandPath], error_context: str = "operation"):
    """Execute configure_delete with error handling."""
    paths = list(paths)
    if not paths:
        return True, None

    response = current_app.device.configure_delete(path=paths)
    if getattr(response, "error", None):
        return False, f"Failed to delete configuration for {error_context}: {response.error}"
    if getattr(response, "status", 200) != 200:
        return False, f"Device returned status {response.status} for {error_context}"
    return True, None
