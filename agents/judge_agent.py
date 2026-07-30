from agents.retry_utils import llm_retry
from openai import OpenAI

from configs.settings import GROQ_API_KEY
from prompts.judge_prompt import JUDGE_SYSTEM_PROMPT, build_judge_prompt


class JudgeAgent:

    def __init__(self):
        self.client = OpenAI(
            api_key=GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1"
        )

    @llm_retry
    def judge(
        self,
        review: str,
        security_findings: str,
        performance_findings: str,
        testing_findings: str,
        architecture_findings: str
    ):
        user_prompt = build_judge_prompt(
            review,
            security_findings,
            performance_findings,
            testing_findings,
            architecture_findings
        )

        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ]
        )

        return response.choices[0].message.content
