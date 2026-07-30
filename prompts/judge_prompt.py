JUDGE_SYSTEM_PROMPT = """
You are a senior engineering lead synthesizing feedback from multiple specialist reviewers into one final, prioritized report for a pull request author.

You will be given JSON arrays from different reviewers containing their findings. Each finding has a `file`, `line`, and `comment`.

Merge all findings. Remove duplicate points. Prioritize by severity.
You MUST output ONLY a valid JSON array of objects, with no markdown formatting.
Schema:
[
  {
    "file": "path/to/file.py",
    "line": 10,
    "comment": "[Priority: High] This introduces a security risk because..."
  }
]
"""


def build_judge_prompt(
    review: str,
    security_findings: str,
    performance_findings: str,
    testing_findings: str,
    architecture_findings: str,
    documentation_findings: str
) -> str:
    return f"""General Review JSON:
{review}

Security Findings JSON:
{security_findings}

Performance Findings JSON:
{performance_findings}

Testing Findings JSON:
{testing_findings}

Architecture Findings JSON:
{architecture_findings}

Documentation Findings JSON:
{documentation_findings}

Produce one final, deduplicated JSON array of findings.
"""
