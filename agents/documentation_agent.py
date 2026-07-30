import os
from openai import OpenAI
from agents.retry_utils import retry_with_backoff

class DocumentationAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        
    @retry_with_backoff()
    def analyze(self, diff_content: str, repo_context: str) -> str:
        prompt = f"""You are a Documentation Expert Agent. Review the code changes for documentation gaps.
        Focus on:
        1. Missing docstrings for new functions and classes.
        2. Vague or unhelpful comments that explain 'what' instead of 'why'.
        3. Hardcoded values or assumptions that are not documented.
        4. Check if the code changes might require updating a README.md.
        
        Repository Context:
        {repo_context}
        
        Code Changes (Diff):
        {diff_content}
        
        Output ONLY a JSON array of findings.
        Schema: [{"file": "path", "line": 42, "comment": "Issue description"}]
        """
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )
        return response.choices[0].message.content
