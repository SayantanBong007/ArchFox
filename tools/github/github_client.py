import requests

from configs.settings import GITHUB_TOKEN


class GitHubClient:

    def get_pr_files(self, owner: str, repo: str, pr_number: int):
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/files"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_pr_details(self, owner: str, repo: str, pr_number: int):
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}

        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()

    def get_pr_diff(self, owner: str, repo: str, pr_number: int) -> str:
        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.diff"
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.text

    def post_pr_comment(self, owner: str, repo: str, pr_number: int, comment_body: str):
        """Post a comment to a GitHub Pull Request."""
        url = f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {"body": comment_body}

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

    def _get_diff_position(self, patch: str, target_line: int) -> int | None:
        """
        Convert an absolute file line number to a GitHub diff position.
        GitHub inline comments require a position = line number within the diff hunk, not file.
        Returns None if the target line is not in the diff.
        """
        if not patch:
            return None

        position = 0
        current_line = 0

        for diff_line in patch.splitlines():
            position += 1
            if diff_line.startswith("@@"):
                # Parse the hunk header e.g. @@ -1,5 +3,8 @@
                import re
                m = re.search(r'\+(\d+)', diff_line)
                if m:
                    current_line = int(m.group(1)) - 1
            elif diff_line.startswith("-"):
                # Removed line — doesn't count as a new file line
                continue
            else:
                # Context (+) or unchanged line
                current_line += 1
                if current_line == target_line:
                    return position

        return None

    def post_inline_pr_comment(self, owner: str, repo: str, pr_number: int,
                               commit_id: str, path: str, line: int, comment_body: str):
        """Post an inline comment to a specific line in a GitHub Pull Request diff."""
        # First, find the diff position for the target line
        pr_files = self.get_pr_files(owner, repo, pr_number)
        position = None
        for f in pr_files:
            if f["filename"].replace("\\", "/") == path.replace("\\", "/"):
                position = self._get_diff_position(f.get("patch", ""), line)
                break

        if position is None:
            raise ValueError(f"Line {line} in '{path}' not found in PR diff — cannot post inline comment.")

        url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3+json"
        }
        data = {
            "body": comment_body,
            "commit_id": commit_id,
            "path": path,
            "position": position,
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()

