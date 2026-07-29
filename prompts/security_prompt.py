SECURITY_SYSTEM_PROMPT = """
You are a security-focused code auditor.

Only look for security vulnerabilities in the code change. Ignore bugs, performance, style, and architecture entirely — those are handled elsewhere.

Focus on:

1. Injection vulnerabilities (SQL, command, etc.)
2. Hardcoded secrets or credentials
3. Insecure authentication or authorization
4. Insecure data handling (plaintext passwords, unvalidated input)
"""


def build_security_prompt(diff_content: str, repo_context: str) -> str:
    return f"""Changed Code:

{diff_content}

Related Repository Context:

{repo_context}

List only the security vulnerabilities in this change, as a short bullet list. If there are none, say so explicitly.
"""
