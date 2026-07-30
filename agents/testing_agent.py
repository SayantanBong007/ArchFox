from agents.retry_utils import llm_retry
from openai import OpenAI

from configs.settings import GROQ_API_KEY
from prompts.testing_prompt import TESTING_SYSTEM_PROMPT, build_testing_prompt


class TestingAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

    @llm_retry
    def analyze(self, diff_content: str, repo_context: str):
        user_prompt = build_testing_prompt(diff_content, repo_context)

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": TESTING_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content
