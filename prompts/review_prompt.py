SYSTEM_PROMPT = """
You are a senior software engineer.

Review the pull request diff.

Focus on:

1. Bugs
2. Security issues
3. Performance concerns
4. Code quality

Provide actionable feedback.
"""


def build_review_prompt(diff_content: str, repo_context: str) -> str:
    return f"""Changed Code:

{diff_content}

Related Repository Context:

{repo_context}

Review this pull request and Return output in:

# Summary

# Bugs

# Security Risks

# Performance Issues

# Architecture Concerns

# Missing Tests

# Recommendations

Focus on:
- Bugs
- Security
- Performance
- Architecture
- Missing tests
"""