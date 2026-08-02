from langchain_groq import ChatGroq
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import SystemMessage

from configs.settings import GROQ_API_KEY
from prompts.database_prompt import DATABASE_SYSTEM_PROMPT
from tools.agent_tools import AGENT_TOOLS

class DatabaseAgent:

    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model="llama-3.1-8b-instant"
        )
        self.agent = create_react_agent(self.llm, AGENT_TOOLS)

    def review(self, diff_content: str, repo_context: str):
        user_prompt = f"Review the following PR diff for database issues.\n\nDIFF:\n{diff_content}\n\nCONTEXT:\n{repo_context}"
        
        messages = [
            SystemMessage(content=DATABASE_SYSTEM_PROMPT),
            {"role": "user", "content": user_prompt}
        ]
        
        response = self.agent.invoke({"messages": messages})
        return response["messages"][-1].content
