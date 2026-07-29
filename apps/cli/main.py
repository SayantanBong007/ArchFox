"""
ArchFox CLI — Run the full PR review pipeline from the command line.

Usage:
    python apps/cli/main.py --repo https://github.com/owner/repo --pr 2
"""
import sys
import os

# Walk up 3 levels: apps/cli/main.py → apps/cli → apps → ArchFox root
# This lets Python find modules like 'graphs', 'agents', 'configs' etc.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import argparse

from configs.logger import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from graphs.pipeline_graph import build_pipeline_graph


def main():
    parser = argparse.ArgumentParser(description="ArchFox — AI Code Reviewer")
    parser.add_argument("--repo", required=True, help="Full GitHub repo URL")
    parser.add_argument("--pr",   required=True, type=int, help="PR number to review")
    args = parser.parse_args()

    repo_url  = args.repo
    pr_number = args.pr

    logger.info(f"ArchFox starting — repo: {repo_url}  PR: #{pr_number}")

    graph = build_pipeline_graph()
    result = graph.invoke({"repo_url": repo_url, "pr_number": pr_number})

    sections = [
        ("REVIEW",                "review"),
        ("SECURITY FINDINGS",     "security_findings"),
        ("PERFORMANCE FINDINGS",  "performance_findings"),
        ("TESTING FINDINGS",      "testing_findings"),
        ("ARCHITECTURE FINDINGS", "architecture_findings"),
        ("FINAL REPORT (Judge)",  "final_report"),
        ("KITSUNE FIX PAYLOAD",   "fix_payload"),
    ]
    for title, key in sections:
        value = result.get(key, "No output.")
        logger.info(f"\n{'='*60}\n{title}\n{'='*60}\n{value}")

    logger.info("ArchFox run complete.")


if __name__ == "__main__":
    main()
