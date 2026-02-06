#!/usr/bin/env python3
# UserPromptSubmit hook: logs each user prompt to logs/prompt_journal.jsonl

import sys
import json
import os
from datetime import datetime, timezone
from pathlib import Path

def main():
    try:
        # Read JSON payload from stdin
        data = json.load(sys.stdin)

        # Extract required fields
        session_id = data.get('session_id')
        prompt = data.get('prompt')

        # Verify fields exist
        if session_id is None or prompt is None:
            # Exit successfully to prevent blocking Claude
            sys.exit(0)

        # Get project root directory
        # Priority 1: Environment variable (set by Claude Code)
        project_dir = os.environ.get('CLAUDE_PROJECT_DIR')

        if project_dir:
            project_dir = Path(project_dir)
        else:
            # Priority 2: Calculate from script location
            # Script should be at: <project>/.claude/hooks/user_prompt_submit.py
            script_path = Path(__file__).resolve()
            # Only use this if the path looks correct (contains .claude/hooks)
            if '.claude' in script_path.parts and 'hooks' in script_path.parts:
                project_dir = script_path.parent.parent.parent
            else:
                # Priority 3: Use current working directory as fallback
                project_dir = Path.cwd()

        # Create logs directory if it doesn't exist
        logs_dir = project_dir / 'logs'
        logs_dir.mkdir(parents=True, exist_ok=True)

        # Prepare log entry with timestamp
        log_entry = {
            'session_id': session_id,
            'prompt': prompt,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Append to JSONL file
        log_file = logs_dir / 'prompt_journal.jsonl'
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

    except (json.JSONDecodeError, KeyError, Exception):
        # Exit successfully even on errors to prevent blocking Claude
        pass

    sys.exit(0)

if __name__ == '__main__':
    main()
