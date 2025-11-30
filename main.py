# main.py
"""
Command-line interface for the Space Knowledge Engine.

This module provides a simple runner for long-running or multi-cycle
processing using the OrchestratorAgent. It is intentionally minimal so the
focus stays on the agent architecture itself.
"""

import argparse
from agents.orchestrator_agent import OrchestratorAgent


def main():
    parser = argparse.ArgumentParser(
        description="Run the Space Knowledge Engine in single or multi-iteration mode."
    )

    parser.add_argument(
        "--iterations",
        type=int,
        default=1,
        help="Number of processing cycles to run."
    )

    parser.add_argument(
        "--interval",
        type=int,
        default=2,
        help="Seconds to wait between cycles (only applies when iterations > 1)."
    )

    args = parser.parse_args()

    orchestrator = OrchestratorAgent()

    if args.iterations == 1:
        # One-shot mode
        orchestrator.run_once()
    else:
        # Multi-cycle mode
        orchestrator.run_continuous(iterations=args.iterations, interval_s=args.interval)


if __name__ == "__main__":
    main()
