"""Run once: uv run python run.py "Write a memo on ACME" """
import sys

from agent import build_agent

if __name__ == "__main__":
    build_agent()(" ".join(sys.argv[1:]) or "Write a research memo on ACME.")  # streams to stdout
    print()
