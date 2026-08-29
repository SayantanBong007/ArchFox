import os
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from agents.retry_utils import llm_retry_tool_calling
from prompts.review_prompt import SYSTEM_PROMPT, build_review_prompt
from tools.agent_tools import AGENT_TOOLS

class ReviewerAgent:

    def __init__(self):
        base_url = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
        model = os.getenv("LLM_MODEL", "openai/gpt-oss-20b")
        
        self.llm = ChatOpenAI(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=base_url,
            model=model,
            max_tokens=2048
        )
        
        # create_react_agent builds a mini-graph that handles the
        # "think -> use tool -> observe -> answer" loop for us!
        self.agent = create_react_agent(self.llm, AGENT_TOOLS)

    @llm_retry_tool_calling
    def review(self, diff_content: str, repo_context: str):
        user_prompt = build_review_prompt(diff_content, repo_context)
        
        # The agent expects a list of messages. We pass the system prompt and the user prompt.
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            {"role": "user", "content": user_prompt}
        ]
        
        # Invoke the agent. It will run in a loop if it needs to use tools.
        response = self.agent.invoke({"messages": messages})
        
        # The final answer is the last message in the sequence
        return response["messages"][-1].content
