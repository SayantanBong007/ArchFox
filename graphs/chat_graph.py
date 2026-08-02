import os
from langgraph.graph import StateGraph, START, END
from graphs.state import ChatState
from agents.chat_agent import ChatAgent
from tools.github.github_client import GitHubClient
from configs.logger import get_logger

logger = get_logger(__name__)

def answer_node(state: ChatState):
    logger.info(f"Chat Graph: Answering question on PR #{state['pr_number']}")
    agent = ChatAgent()
    reply = agent.chat(
        owner=state["owner"],
        repo=state["repo_name"],
        pr_number=state["pr_number"],
        comment_body=state["comment_body"]
    )
    return {"reply_body": reply}

def post_reply_node(state: ChatState):
    logger.info(f"Chat Graph: Posting reply to GitHub PR #{state['pr_number']}")
    client = GitHubClient()
    
    # We prefix with a small emoji so they know it's ArchFox answering
    reply_with_prefix = f"🦊 **ArchFox Chat:**\n\n{state['reply_body']}"
    
    client.post_pr_comment(
        owner=state["owner"],
        repo=state["repo_name"],
        pr_number=state["pr_number"],
        comment_body=reply_with_prefix
    )
    return {}

def build_chat_graph():
    graph = StateGraph(ChatState)  # type: ignore

    graph.add_node("answer", answer_node)
    graph.add_node("post_reply", post_reply_node)

    graph.add_edge(START, "answer")
    graph.add_edge("answer", "post_reply")
    graph.add_edge("post_reply", END)

    return graph.compile()
