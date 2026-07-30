"""Fix Planner Agent — Generates a PR Comment payload containing a code fix.

This agent takes the Root Cause Analysis from the Investigator, and generates
a structured payload (Markdown diff) that can be sent to ArchFox. 

CRITICAL SAFETY GUARANTEE:
This agent NEVER writes to the source files directly. It purely returns a 
payload that a system like ArchFox can post to a GitHub PR for Human-in-the-Loop review.
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

PLANNER_PROMPT = """You are an elite AI Fix Planner.
You have been handed a Root Cause Analysis for a bug, along with the actual PR diff.

YOUR TASK:
Generate the exact Markdown payload that will be posted as a comment on a GitHub Pull Request.
This comment must clearly explain the fix and provide the before/after code blocks.

FORMAT EXPECTED:
# ArchFox Bug Fix Proposal

**Root Cause Summary:**
[Brief 1-2 sentence summary of what was found]

**Target File:** `[relative file path, e.g. services/user_service.py]`
**Target Line:** [IMPORTANT: This MUST be the line number of one of the new lines (starting with +) from the PR diff provided below. Count from line 1 of the file.]

**Proposed Change:**
```diff
- [old code]
+ [new code]
```

RULES:
- Be concise.
- Output ONLY the Markdown payload. Do not include any conversational text.
- The diff should only include the specific lines being changed, plus a couple lines of context.
- The Target File must be a relative path matching the PR diff (e.g. `services/user_service.py`, NOT `data/repos/Dummy/services/user_service.py`).
- The Target Line MUST be an added line (+) from the PR diff. Study the diff carefully to find its exact line number in the file.
"""


class FixPlanner:
    """Agent that translates an investigation into a PR Comment Payload."""

    def __init__(self):
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
        self.model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def generate_payload(self, investigation_result: str, pr_diff: str = ""):
        """Generate the PR Comment Payload and stream it."""
        
        logger.info("Generating Fix Payload for ArchFox...")
        
        user_message = f"PR DIFF (use this to determine Target File and Target Line):\n{pr_diff}\n\nROOT CAUSE ANALYSIS FROM INVESTIGATOR:\n{investigation_result}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": PLANNER_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                stream=True,
                temperature=0.1
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[Planner Error: {e}]"
