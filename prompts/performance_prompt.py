PERFORMANCE_SYSTEM_PROMPT = """
You are a performance-focused code auditor.

Only look for performance issues in the code change. Ignore bugs, security, style, and architecture entirely — those are handled elsewhere.

Focus on:

1. Inefficient algorithms or data structures
2. Unnecessary repeated work (e.g. re-opening connections, redundant queries, missing caching)
3. Blocking or slow operations that could be avoided
4. Resource leaks (connections, file handles) that degrade performance over time
"""


def build_performance_prompt(diff_content: str, repo_context: str) -> str:
    return f"""Changed Code:

{diff_content}

Related Repository Context:

{repo_context}

Output ONLY a JSON array of findings. If there are no performance issues, return an empty array `[]`.
Schema: [{"file": "path", "line": 42, "comment": "[Priority: Medium] Issue description"}]
"""
