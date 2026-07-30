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

    # ---------------------------------------------------------
    # POST TO GITHUB
    # ---------------------------------------------------------
    try:
        repo_parts = repo_url.rstrip("/").split("/")
        repo_name = repo_parts[-1]
        owner = repo_parts[-2]
        
        comment_body = f"# 🦊 ArchFox AI Code Review\n\n"
        if "final_report" in result:
            comment_body += f"{result['final_report']}\n\n"
            
        if "fix_payload" in result:
            comment_body += "---\n### 🛠️ Suggested Fixes\n\n"
            comment_body += f"{result['fix_payload']}\n"

        from tools.github.github_client import GitHubClient
        client = GitHubClient()
        client.post_pr_comment(owner, repo_name, pr_number, comment_body)
        logger.info("Successfully posted review to GitHub PR!")
    except Exception as e:
        logger.error(f"Failed to post to GitHub: {e}")

    logger.info("ArchFox run complete.")


if __name__ == "__main__":
    main()
