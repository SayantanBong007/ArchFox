"""Fix Agent — Connects ArchFox to the Kitsune Knowledge Base.

When ArchFox's Judge finds a critical issue in a PR, this agent calls
Kitsune to do a deep dive and generate a Markdown payload to fix the issue.
"""

import os
import sys

# Ensure the root of ArchFox is in the python path
ARCHFOX_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ARCHFOX_ROOT not in sys.path:
    sys.path.insert(0, ARCHFOX_ROOT)

from kitsune.agents.investigator import IssueInvestigator
from kitsune.agents.planner import FixPlanner

from tools.kitsune_engine import active_engine, get_engine


class FixAgent:
    """Uses Kitsune to generate a fix payload for a given PR finding."""

    def __init__(self, namespace: str | None = None):
        # Search the index of the repository under review (or a given namespace),
        # sharing its stores instead of opening a second copy.
        engine = get_engine(namespace) if namespace is not None else active_engine()
        self.investigator = IssueInvestigator(searcher=engine.searcher)
        self.planner = FixPlanner()

    def generate_fix_payload(self, bug_report: str, pr_diff: str = "") -> str:
        """Runs the Investigator -> Planner Kitsune pipeline."""

        # Step 1: Kitsune Investigator finds the root cause using the knowledge graph
        investigation_result = ""
        for chunk in self.investigator.investigate(bug_report):
            investigation_result += chunk

        # Step 2: Kitsune Planner generates the Markdown diff payload
        # We pass the PR diff so the planner can pick a valid Target Line
        payload_result = ""
        for chunk in self.planner.generate_payload(investigation_result, pr_diff=pr_diff):
            payload_result += chunk

        return payload_result
