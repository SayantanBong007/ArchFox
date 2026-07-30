"""Issue Investigation Agent — Acts like a senior engineer debugging a bug report.

This agent uses the Hybrid Query Engine to find relevant code based on a bug report,
then uses the LLM to analyze the code and propose a root cause and fix.
"""

import os
import logging
from openai import OpenAI

from kitsune.query.hybrid_search import HybridSearcher

logger = logging.getLogger(__name__)

INVESTIGATOR_PROMPT = """You are an elite AI Debugging Engineer.
You have been assigned a bug report to investigate.

Below is the context retrieved from the repository's Knowledge Graph (Kitsune).
It contains the code most likely related to the bug, as well as the functions it depends on.

YOUR TASK:
1. Identify the Root Cause: Read the code and determine exactly why the bug is happening.
2. Pinpoint the Location: State exactly which file and function is causing the issue.
3. Propose a Fix: Explain how you would rewrite or fix the code to resolve the bug.

RULES:
- Be incredibly precise.
- Only base your reasoning on the provided code context.
- Format your response with clear headers: "Root Cause", "Location", and "Proposed Fix".
"""


class IssueInvestigator:
    """Agent that investigates bug reports using Kitsune."""

    def __init__(self, chroma_path: str | None = None):
        self.searcher = HybridSearcher(chroma_path=chroma_path)
        
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
        self.model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        
        self.client = OpenAI(base_url=base_url, api_key=api_key)

    def _format_context(self, search_results: dict) -> str:
        """Format the hybrid search results into a readable context block."""
        context = ""
        
        primary = search_results.get("primary_chunks", [])
        if primary:
            context += "--- RELEVANT CODE ---\n"
            for chunk in primary:
                name = chunk.get("name", "Unknown")
                file_path = chunk.get("file_path", "Unknown")
                context += f"\nFile: {file_path} | Function: {name}\n"
                context += f"```python\n{chunk.get('text', '')}\n```\n"

        deps = search_results.get("dependency_chunks", [])
        if deps:
            context += "\n--- GRAPH DEPENDENCIES (functions called by the above code) ---\n"
            for chunk in deps:
                name = chunk.get("name", "Unknown")
                file_path = chunk.get("file_path", "Unknown")
                context += f"\nFile: {file_path} | Function: {name}\n"
                context += f"```python\n{chunk.get('text', '')}\n```\n"
                
        return context

    def investigate(self, bug_report: str):
        """Investigate a bug report and stream the analysis."""
        
        # 1. Ask Kitsune to find the code related to the bug report
        logger.info(f"Querying Hybrid Engine for bug report: '{bug_report[:30]}...'")
        
        # We fetch a bit more context (k=3) for debugging
        search_results = self.searcher.search(bug_report, k_primary=3)
        context_str = self._format_context(search_results)
        
        user_message = f"BUG REPORT:\n{bug_report}\n\nREPOSITORY CONTEXT:\n{context_str}"
        
        # 2. Ask the LLM to act as the Detective
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": INVESTIGATOR_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                stream=True,
                temperature=0.2  # Slightly higher than 0.1 for more expressive explanations, but still grounded
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[Agent Error: {e}]"
