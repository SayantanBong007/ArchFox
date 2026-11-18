import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from git import Repo


def _with_token(repo_url: str, token: str) -> str:
    """https://github.com/o/r -> https://x-access-token:<token>@github.com/o/r"""
    parts = urlsplit(repo_url)
    if parts.scheme != "https" or "@" in parts.netloc:
        return repo_url
    return urlunsplit(parts._replace(netloc=f"x-access-token:{token}@{parts.netloc}"))


class GitCloneTool:

    def clone_repo(self, repo_url: str, repo_name: str):
        target_dir = Path("data/repos") / repo_name

        if target_dir.exists():
            return str(target_dir)

        # Private repositories need credentials. In GitHub Actions the workflow's
        # GITHUB_TOKEN can read the repository it runs in, so use it when present.
        token = os.getenv("GITHUB_TOKEN")
        if token:
            repo = Repo.clone_from(_with_token(repo_url, token), target_dir)
            # Don't leave the token in the clone's .git/config.
            repo.remotes.origin.set_url(repo_url)
        else:
            Repo.clone_from(repo_url, target_dir)
        return str(target_dir)
