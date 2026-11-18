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


def build_summary_comment(final_report: str, fix_payload: str) -> str:
    """The PR summary comment: the judge's prose plus one readable list of findings.

    The judge's report contains its findings as a JSON array, and fix_payload is the same
    array re-serialised, so posting both raw showed every finding twice. Show the prose
    without the JSON (and without any <thinking> block), then the findings as a list.
    """
    import json
    import re

    body = "# 🦊 ArchFox AI Code Review\n\n"

    prose = re.sub(r"<thinking>.*?</thinking>", "", final_report or "", flags=re.DOTALL)
    prose = re.sub(r"```.*?```", "", prose, flags=re.DOTALL)            # fenced JSON
    prose = re.sub(r"^\s*\[\s*\{.*\}\s*\]\s*$", "", prose, flags=re.DOTALL | re.MULTILINE)
    prose = prose.strip()

    try:
        findings = json.loads(fix_payload)
        if not isinstance(findings, list):
            raise ValueError
    except (TypeError, ValueError):
        # Couldn't parse the findings: fall back to posting the raw report.
        return body + f"{final_report}\n"

    if prose:
        body += prose + "\n\n"
    if findings:
        body += "### Findings\n\n"
        for f in findings:
            where = f"`{f.get('file', '?')}:{f.get('line', '?')}`"
            body += f"- {where} — {f.get('comment', '').strip()}\n"
        body += "\n_Inline comments were posted on the matching lines of the diff where possible._\n"
    else:
        body += "No issues found. ✅\n"
    return body


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
        ("DOCUMENTATION FINDINGS","documentation_findings"),
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
        repo_name = repo_parts[-1].replace(".git", "")
        owner = repo_parts[-2]
        
        comment_body = build_summary_comment(result.get("final_report", ""),
                                             result.get("fix_payload", ""))

        from tools.github.github_client import GitHubClient
        client = GitHubClient()
        client.post_pr_comment(owner, repo_name, pr_number, comment_body)
        logger.info("Successfully posted review to GitHub PR!")
    except Exception as e:
        logger.error(f"Failed to post to GitHub: {e}")

    logger.info("ArchFox run complete.")


if __name__ == "__main__":
    main()
