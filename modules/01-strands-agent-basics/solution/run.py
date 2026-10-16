"""Run the agent once: uv run python run.py "How much is 112.4 vs 98.2 in percent change?" """
import sys

from agent import build_agent

if __name__ == "__main__":
    prompt = " ".join(sys.argv[1:]) or "Price moved from 98.2 to 112.4. What is the percent change?"
    build_agent()(prompt)  # Strands streams the reply to stdout as it arrives
    print()
