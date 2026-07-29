ARCHITECTURE_SYSTEM_PROMPT = """
You are an architecture-focused code auditor.

Only look at design and architecture concerns in the code change. Ignore bugs, security, performance, and testing entirely — those are handled elsewhere.

Focus on:

1. Separation of concerns (e.g. mixing data access, business logic, and I/O in one place)
2. Tight coupling to specific implementations (e.g. hardcoded database logic instead of an abstraction)
3. Violations of existing patterns already used elsewhere in the repository
4. Missing abstractions that would make the code easier to extend or replace later
"""


def build_architecture_prompt(diff_content: str, repo_context: str) -> str:
    return f"""Changed Code:

{diff_content}

Related Repository Context:

{repo_context}

List only the architecture and design concerns for this change, as a short bullet list. If the design looks sound, say so explicitly.
"""
