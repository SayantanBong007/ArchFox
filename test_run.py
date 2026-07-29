"""
ArchFox — Test Runner
Logs to: archfox.log (project root, cleared on every run) + console.
"""
import sys
import io
import os

# Force UTF-8 on Windows terminals
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# Force HuggingFace to use cached models — no network needed
os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

# Setup logging FIRST — before any project imports
from configs.logger import setup_logging, get_logger, LOG_FILE
setup_logging()
logger = get_logger(__name__)

from graphs.pipeline_graph import build_pipeline_graph


def main():
    repo_url = "https://github.com/SayantanBong007/Dummy"
    pr_number = 2

    logger.info(f"ArchFox starting — repo: {repo_url}  PR: #{pr_number}")
    logger.info(f"Log file: {LOG_FILE}")

    graph = build_pipeline_graph()
    result = graph.invoke({"repo_url": repo_url, "pr_number": pr_number})

    sections = [
        ("REVIEW",               "review"),
        ("SECURITY FINDINGS",    "security_findings"),
        ("PERFORMANCE FINDINGS", "performance_findings"),
        ("TESTING FINDINGS",     "testing_findings"),
        ("ARCHITECTURE FINDINGS","architecture_findings"),
        ("FINAL REPORT (Judge)", "final_report"),
        ("KITSUNE FIX PAYLOAD",  "fix_payload"),
    ]

    for title, key in sections:
        value = result.get(key, "No output.")
        logger.info(f"\n{'='*60}\n{title}\n{'='*60}\n{value}")

    logger.info("ArchFox run complete.")


if __name__ == "__main__":
    main()
