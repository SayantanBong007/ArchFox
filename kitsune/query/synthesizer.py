"""LLM Synthesizer — takes hybrid context and streams an answer.

This script formats the context (primary chunks + dependencies),
constructs a strict prompt, and calls the LLM via the OpenAI client
(which we point to Groq via .env for blazing fast inference).
"""

import os
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Kitsune, an expert AI software architect. 
You are answering a question about a codebase.

You have been provided with two types of context:
1. PRIMARY CHUNKS: The core code blocks relevant to the question.
2. DEPENDENCIES: Code blocks that the primary chunks call/depend on.

RULES:
1. Answer the question comprehensively using ONLY the provided code.
2. If you don't know the answer based on the context, say so. Do not guess.
3. Cite the functions/classes you are referencing.
4. Keep your answer clear, structured, and developer-friendly.
"""


class Synthesizer:
    """Takes retrieved context and generates an LLM response."""

    def __init__(self):
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        api_key = os.getenv("LLM_API_KEY", os.getenv("GROQ_API_KEY", ""))
        self.model = os.getenv("LLM_MODEL", "llama-3.1-8b-instant")
        
        if not api_key:
            logger.warning("No LLM_API_KEY or GROQ_API_KEY found! LLM queries will fail.")
            
        self.client = OpenAI(
            base_url=base_url,
            api_key=api_key
        )

    def _format_context(self, search_results: dict) -> str:
        """Format the primary chunks and dependencies into a readable string."""
        context = ""
        
        primary = search_results.get("primary_chunks", [])
        if primary:
            context += "--- PRIMARY CHUNKS ---\n"
            for chunk in primary:
                name = chunk.get("name", "Unknown")
                file_path = chunk.get("file_path", "Unknown")
                context += f"\nFile: {file_path} | Symbol: {name}\n"
                context += f"```python\n{chunk.get('text', '')}\n```\n"

        deps = search_results.get("dependency_chunks", [])
        if deps:
            context += "\n--- GRAPH DEPENDENCIES (called by primary chunks) ---\n"
            for chunk in deps:
                name = chunk.get("name", "Unknown")
                file_path = chunk.get("file_path", "Unknown")
                context += f"\nFile: {file_path} | Symbol: {name}\n"
                context += f"```python\n{chunk.get('text', '')}\n```\n"
                
        return context

    def generate_answer(self, question: str, search_results: dict):
        """Send prompt to LLM and yield streaming response chunks."""
        context_str = self._format_context(search_results)
        
        user_message = f"CONTEXT:\n{context_str}\n\nQUESTION:\n{question}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_message}
                ],
                stream=True,
                temperature=0.1
            )
            
            for chunk in response:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"\n\n[LLM Error: {e}]"
