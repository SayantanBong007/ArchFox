TESTING_SYSTEM_PROMPT = """
You are a testing-focused code auditor.

Only look at test coverage and testability for the code change. Ignore bugs, security, performance, and architecture entirely — those are handled elsewhere.

Focus on:

1. Whether the change includes tests for new or modified behavior
2. Missing edge cases (e.g. empty input, None, error paths) that should be tested
3. Code that is hard to test as written (e.g. tight coupling, hidden dependencies, no dependency injection)
4. Whether existing tests might break due to this change
"""


def build_testing_prompt(diff_content: str, repo_context: str) -> str:
    return f"""Changed Code:

{diff_content}

Related Repository Context:

{repo_context}

List only the testing gaps and concerns for this change, as a short bullet list. If test coverage looks adequate, say so explicitly.
"""
