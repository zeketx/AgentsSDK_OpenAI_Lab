#!/usr/bin/env python3
"""PreToolUse hook that blocks access to sensitive files."""

import json
import shlex
import sys
from pathlib import Path


SENSITIVE_EXACT = {
    ".env",
    "gmail_credentials.json",
    "gmail_token.pickle",
}

SENSITIVE_ENV_SAFE_SUFFIXES = {
    ".env.example",
    ".env.sample",
    ".env.template",
}

SHELL_SEPARATORS = {"|", "||", "&&", ";", "<", ">", ">>", "<<", "2>", "2>>"}


def is_sensitive_name(name: str) -> bool:
    lowered = name.lower()
    if lowered in SENSITIVE_EXACT:
        return True
    if lowered.startswith(".env.") and lowered not in SENSITIVE_ENV_SAFE_SUFFIXES:
        return True
    return False


def normalize_path(candidate: str, cwd: str) -> Path:
    path = Path(candidate).expanduser()
    if not path.is_absolute():
        path = Path(cwd) / path
    try:
        return path.resolve()
    except Exception:
        return path


def parse_bash_candidates(command: str) -> list[str]:
    try:
        tokens = shlex.split(command)
    except ValueError:
        tokens = command.split()

    candidates: list[str] = []
    for token in tokens:
        if not token or token in SHELL_SEPARATORS:
            continue
        if token.startswith("-"):
            continue
        if "://" in token:
            continue
        if "=" in token and not token.startswith((".", "/", "~")):
            continue
        candidates.append(token.strip("\"'"))
    return candidates


def deny(reason: str) -> None:
    output = {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }
    print(json.dumps(output))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_name = payload.get("tool_name")
    tool_input = payload.get("tool_input", {})
    cwd = str(payload.get("cwd", "."))

    if tool_name == "Read":
        file_path = str(tool_input.get("file_path", ""))
        if file_path:
            resolved = normalize_path(file_path, cwd)
            if is_sensitive_name(resolved.name):
                deny(f"Blocked sensitive file read: {resolved.name}")
                return 0

    if tool_name == "Grep":
        grep_path = str(tool_input.get("path", ""))
        if grep_path:
            resolved = normalize_path(grep_path, cwd)
            if is_sensitive_name(resolved.name):
                deny(f"Blocked Grep on sensitive file: {resolved.name}")
                return 0

    if tool_name == "Glob":
        glob_pattern = str(tool_input.get("pattern", ""))
        glob_path = str(tool_input.get("path", ""))
        # Block if the pattern itself is a sensitive filename
        if glob_pattern and is_sensitive_name(Path(glob_pattern).name):
            deny(f"Blocked Glob on sensitive file: {Path(glob_pattern).name}")
            return 0
        # Block if path points directly to a sensitive file
        if glob_path:
            resolved = normalize_path(glob_path, cwd)
            if is_sensitive_name(resolved.name):
                deny(f"Blocked Glob on sensitive file: {resolved.name}")
                return 0

    if tool_name == "Bash":
        command = str(tool_input.get("command", ""))
        for candidate in parse_bash_candidates(command):
            resolved = normalize_path(candidate, cwd)
            if is_sensitive_name(resolved.name):
                deny(
                    "Blocked Bash command that references a sensitive file: "
                    f"{resolved.name}"
                )
                return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
