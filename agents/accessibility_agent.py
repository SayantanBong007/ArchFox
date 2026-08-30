import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from agents.retry_utils import llm_retry_tool_calling
from prompts.accessibility_prompt import ACCESSIBILITY_SYSTEM_PROMPT
from tools.agent_tools import AGENT_TOOLS

class AccessibilityAgent:

    def __init__(self):
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
        
        self.llm = ChatOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=base_url,
            model=model,
            max_tokens=2048,
            reasoning_effort="low"
        )
        self.agent = create_react_agent(self.llm, AGENT_TOOLS)

    @llm_retry_tool_calling
    def review(self, diff_content: str, repo_context: str):
        user_prompt = f"Review the following PR diff for accessibility issues.\n\nDIFF:\n{diff_content}\n\nCONTEXT:\n{repo_context}"
        
        messages = [
            SystemMessage(content=ACCESSIBILITY_SYSTEM_PROMPT),
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.agent.invoke({"messages": messages})
        return response["messages"][-1].content
