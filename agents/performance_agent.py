from agents.retry_utils import llm_retry
from openai import OpenAI

from configs.settings import GROQ_API_KEY
from prompts.performance_prompt import PERFORMANCE_SYSTEM_PROMPT, build_performance_prompt


class PerformanceAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

    @llm_retry
    def analyze(self, diff_content: str, repo_context: str):
        user_prompt = build_performance_prompt(diff_content, repo_context)

        response = self.client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": PERFORMANCE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content
