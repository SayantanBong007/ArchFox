import os
import sys
import threading

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fastapi import FastAPI, Request, BackgroundTasks
from configs.logger import setup_logging, get_logger
from graphs.chat_graph import build_chat_graph

setup_logging()
logger = get_logger(__name__)

app = FastAPI(title="ArchFox Webhook Server")

# Instantiate graph globally
chat_graph = build_chat_graph()

def process_chat_graph_async(owner: str, repo_name: str, pr_number: int, comment_body: str):
    try:
        logger.info(f"Triggering Chat Graph for PR {pr_number} on {owner}/{repo_name}")
        chat_graph.invoke({
            "owner": owner,
            "repo_name": repo_name,
            "pr_number": pr_number,
            "comment_body": comment_body
        })
        logger.info(f"Chat Graph completed successfully for PR {pr_number}")
    except Exception as e:
        logger.error(f"Error executing chat graph: {e}")

@app.post("/webhook")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    # We only care about issue comments (Pull Requests are issues in the GitHub API)
    if "issue" in payload and "comment" in payload:
        action = payload.get("action")
        # Only trigger on new comments
        if action != "created":
            return {"status": "ignored", "reason": "not a new comment"}
            
        # We only care about PRs, not regular issues
        if "pull_request" not in payload["issue"]:
            return {"status": "ignored", "reason": "not a pull request comment"}
            
        comment_body = payload["comment"].get("body", "").strip()
        
        # Check if ArchFox is mentioned
        if "@archfox" in comment_body.lower():
            # Extract PR number
            pr_number = payload["issue"].get("number")
            
            # Extract repo details
            repository = payload.get("repository", {})
            repo_name = repository.get("name")
            owner = repository.get("owner", {}).get("login")
            
            if not all([pr_number, repo_name, owner]):
                return {"status": "ignored", "reason": "missing repo details"}

            # Clean up the mention from the comment
            cleaned_comment = comment_body.lower().replace("@archfox chat", "").replace("@archfox", "").strip()
            
            # Fire the LangGraph pipeline in the background and return 202 immediately to GitHub
            background_tasks.add_task(process_chat_graph_async, owner, repo_name, pr_number, cleaned_comment)
            
            return {"status": "accepted", "message": "Chat graph triggered"}
            
    return {"status": "ignored", "reason": "unsupported event"}

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting ArchFox Webhook Server on port 8000...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
