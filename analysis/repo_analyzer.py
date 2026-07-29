import ast
import json
from pathlib import Path


class RepoAnalyzer:
    def analyze(self, repo_path: str) -> dict:
        dependency_map = {}

        for file in Path(repo_path).rglob("*.py"):
            try:
                content = file.read_text(
                    encoding="utf-8",
                    errors="ignore"
                )

                tree = ast.parse(content)

                imports = []

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.append(alias.name)

                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.append(node.module)

                dependency_map[str(file)] = imports

            except Exception:
                continue

        return dependency_map

    def save(self, architecture: dict, output_path: str = "data/architecture.json"):
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(json.dumps(architecture, indent=2))