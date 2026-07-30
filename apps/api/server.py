from fastapi import FastAPI, Request, BackgroundTasks
import uvicorn

from configs.logger import get_logger
from tools.github.github_client import GitHubClient

logger = get_logger(__name__)

app = FastAPI(title="ArchFox Webhook Server")

def process_comment(owner: str, repo: str, pr_number: int, comment_body: str, comment_id: int):
    """Background task to process the comment and reply."""
    logger.info(f"Processing comment {comment_id} on {owner}/{repo}#{pr_number}")
    
    # We will invoke ChatAgent here!
    from agents.chat_agent import ChatAgent
    agent = ChatAgent()
    reply = agent.chat(owner, repo, pr_number, comment_body)
    
    # Post the reply
    github_client = GitHubClient()
    github_client.post_pr_comment(owner, repo, pr_number, reply)
    logger.info("Successfully posted reply!")

@app.post("/webhook/github")
async def github_webhook(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    
    # We only care about PR comments being created
    if "action" in payload and payload["action"] == "created" and "comment" in payload:
        comment_body = payload["comment"].get("body", "")
        
        # Check if ArchFox was mentioned
        if "@archfox" in comment_body.lower():
            owner = payload["repository"]["owner"]["login"]
            repo = payload["repository"]["name"]
            
            # issues and PRs use the same comment webhook format
            issue_data = payload.get("issue", {})
            pr_number = issue_data.get("number")
            comment_id = payload["comment"]["id"]
            
            if pr_number:
                # Dispatch background task so we can return 200 immediately to GitHub
                background_tasks.add_task(process_comment, owner, repo, pr_number, comment_body, comment_id)
                return {"status": "accepted", "message": "Processing comment."}
                
    return {"status": "ignored"}

if __name__ == "__main__":
    uvicorn.run("apps.api.server:app", host="0.0.0.0", port=8000, reload=True)
