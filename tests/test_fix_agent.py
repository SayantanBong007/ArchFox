import sys
import os
import io

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from dotenv import load_dotenv
load_dotenv()

from agents.fix_agent import FixAgent


def main():
    print("Testing ArchFox's internal Kitsune FixAgent...")
    
    try:
        agent = FixAgent()
        print("✅ FixAgent initialized successfully (Kitsune imported).")
    except Exception as e:
        print(f"❌ Failed to initialize FixAgent: {e}")
        return

    bug_report = "BUG REPORT: We are getting empty docstrings for all class definitions when we parse a file."
    
    print("\n[🦊 Sending test bug report to Kitsune...]")
    try:
        payload = agent.generate_fix_payload(bug_report)
        print("\n✅ Successfully generated payload!")
        print("-" * 50)
        print(payload)
        print("-" * 50)
    except Exception as e:
        print(f"\n❌ Failed to generate payload: {e}")

if __name__ == "__main__":
    main()
