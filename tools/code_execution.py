# tools/code_execution.py
"""
code_execution.py

Utility for safely executing isolated Python snippets.  This is used to
demonstrate the “Tool Use” concept without exposing the system to arbitrary code
execution risks.

Important notes:
- Runs code in a separate subprocess.
- Enforces a timeout.
- Captures stdout and stderr.
- Never intended as a production sandbox for untrusted users.
"""

import subprocess
import sys
from typing import Optional


class CodeExecutor:
    def __init__(self, timeout_seconds: int = 5):
        """
        timeout_seconds: maximum allowed runtime for a snippet.
        """
        self.timeout = timeout_seconds

    def execute(self, code_str: str) -> str:
        """
        Execute a Python code snippet in an isolated subprocess.

        Returns:
            - stdout if execution succeeds,
            - stderr or timeout message otherwise.
        """
        if not isinstance(code_str, str) or not code_str.strip():
            return "Error: empty or invalid code snippet."

        try:
            result = subprocess.run(
                [sys.executable, "-c", code_str],
                capture_output=True,
                text=True,
                timeout=self.timeout,
            )
        except subprocess.TimeoutExpired:
            return "Error: execution timed out."
        except Exception as exc:
            return f"Error: {exc}"

        if result.returncode == 0:
            return result.stdout.strip()
        else:
            return f"Error: {result.stderr.strip()}"

    # alias for convenience
    run = execute


# Simple CLI demo
if __name__ == "__main__":
    executor = CodeExecutor()
    snippet = "print('Hello from sandbox!')"
    out = executor.execute(snippet)
    print("Output:", out)
