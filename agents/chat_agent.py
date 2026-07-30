import os
from openai import OpenAI

from configs.logger import get_logger
from kitsune.engine.knowledge_engine import RepositoryKnowledgeEngine
from tools.git.git_clone import GitCloneTool

logger = get_logger(__name__)

class ChatAgent:
    def __init__(self):
        self.client = OpenAI(
            base_url="https://api.groq.com/openai/v1",
            api_key=os.environ.get("GROQ_API_KEY")
        )
        self.engine = RepositoryKnowledgeEngine()
        self.cloner = GitCloneTool()
        
    def chat(self, owner: str, repo: str, pr_number: int, comment_body: str) -> str:
        logger.info("ChatAgent is processing a user question...")
        
        # Clone repo to ensure we have it locally for GraphRAG
        repo_url = f"https://github.com/{owner}/{repo}.git"
        repo_path = self.cloner.clone_repo(repo_url, repo)
        
        # We assume the repo is already indexed from the PR CI/CD run!
        # Perform GraphRAG semantic search based on the user's comment
        context = self.engine.search_semantic(query=comment_body)
        
        prompt = f"""You are ArchFox, a senior AI Software Engineer.
You are replying to a developer's comment on a Pull Request.

User Comment:
{comment_body}

Repository Context (GraphRAG):
{context}

Reply directly and helpfully to the user based on the context provided. 
If the user asks why you flagged something, explain it using the context.
Keep your response professional but concise. Use markdown formatting.
"""
        response = self.client.chat.completions.create(
            model=os.getenv("LLM_MODEL", "llama-3.1-8b-instant"),
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
