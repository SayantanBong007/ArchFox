import os
from openai import OpenAI

from configs.logger import get_logger
from tools.kitsune_engine import namespace_for, set_active
from tools.git.git_clone import GitCloneTool
from tools.github.github_client import GitHubClient
from prompts.chat_prompt import CHAT_SYSTEM_PROMPT, build_chat_prompt

logger = get_logger(__name__)

class ChatAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url=os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key=os.getenv("GROQ_API_KEY", "token-sentry")
        )
        self.cloner = GitCloneTool()
        self.github = GitHubClient()
        
    def chat(self, owner: str, repo: str, pr_number: int, comment_body: str) -> str:
        logger.info("ChatAgent is processing a user question...")
        
        # Clone repo to ensure we have it locally for GraphRAG
        repo_url = f"https://github.com/{owner}/{repo}.git"
        repo_path = self.cloner.clone_repo(repo_url, repo)
        
        # Fetch the actual PR diff!
        diff_content = self.github.get_pr_diff(owner, repo, pr_number)
        
        # This repo's own Kitsune index. Indexing is incremental, so if the PR review
        # already indexed it on this machine, only changed files are re-read.
        engine = set_active(namespace_for(owner, repo))
        engine.index_repository(repo_path)

        # Graph RAG search (meaning + keywords + call graph) based on the user's comment
        context = engine.search_semantic(query=comment_body)
        
        prompt = build_chat_prompt(comment_body, diff_content, context)
        
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "openai/gpt-oss-20b"),
            messages=[
                {"role": "system", "content": CHAT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            reasoning_effort="low"
        )
        return response.choices[0].message.content or ""
