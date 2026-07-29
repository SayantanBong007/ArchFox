from pathlib import Path


class RepoSummary:

    def summarize(self, repo_path):
        py_files = len(list(Path(repo_path).rglob("*.py")))
        md_files = len(list(Path(repo_path).rglob("*.md")))
        return f"""
Repository Summary

Python Files: {py_files}
Markdown Files: {md_files}
"""
