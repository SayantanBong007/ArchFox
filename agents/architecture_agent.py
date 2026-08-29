import os
from agents.retry_utils import llm_retry
from openai import OpenAI

from configs.settings import GROQ_API_KEY
from prompts.architecture_prompt import ARCHITECTURE_SYSTEM_PROMPT, build_architecture_prompt


class ArchitectureAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=os.getenv("GROQ_API_KEY", "token-sentry"),
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        )

    @llm_retry
    def analyze(self, diff_content: str, repo_context: str):
        user_prompt = build_architecture_prompt(diff_content, repo_context)

        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "groq/compound-mini"),
            messages=[
                {"role": "system", "content": ARCHITECTURE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content
