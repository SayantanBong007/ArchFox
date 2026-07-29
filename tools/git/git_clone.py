from pathlib import Path
from git import Repo


class GitCloneTool:

    def clone_repo(self, repo_url: str, repo_name: str):
        target_dir = Path("data/repos") / repo_name

        if target_dir.exists():
            return str(target_dir)

        Repo.clone_from(repo_url, target_dir)
        return str(target_dir)
