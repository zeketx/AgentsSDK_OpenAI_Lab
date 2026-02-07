#!/usr/bin/env python3
# PostToolUse hook: logs successful tool usage to logs/post_tool_use.jsonl for observability

import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path


def main():
    try:
        data = json.load(sys.stdin)

        session_id = data.get("session_id")
        tool_name = data.get("tool_name")
        tool_input = data.get("tool_input")

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR")
        if project_dir:
            project_dir = Path(project_dir)
        else:
            script_path = Path(__file__).resolve()
            if ".claude" in script_path.parts and "hooks" in script_path.parts:
                project_dir = script_path.parent.parent.parent
            else:
                project_dir = Path.cwd()

        logs_dir = project_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        log_entry = {
            "session_id": session_id,
            "tool_name": tool_name,
            "tool_input": tool_input,
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

        with open(logs_dir / "post_tool_use.jsonl", "a") as f:
            f.write(json.dumps(log_entry) + "\n")

    except Exception:
        pass

    sys.exit(0)


if __name__ == "__main__":
    main()
