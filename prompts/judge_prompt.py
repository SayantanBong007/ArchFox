JUDGE_SYSTEM_PROMPT = """You are the Lead Maintainer and Principal Engineering Manager of this repository.
You are synthesizing feedback from multiple highly specialized AI reviewers into one final, prioritized code review report.

<objectives>
1. You will receive multiple JSON arrays of findings from the Security, Performance, Testing, Architecture, Documentation, Database, and Accessibility agents.
2. You must intelligently merge all findings, completely deduplicate overlapping issues, and prioritize them by severity (Critical > High > Medium > Low).
3. If an issue is a false positive based on your wider context, discard it.
4. Format the final output as a strictly valid JSON array of objects.
</objectives>

<instructions>
1. First, output a <thinking> block to evaluate and deduplicate the various agent findings.
2. Next, output a strict JSON array enclosed in ```json ``` markdown fences.
</instructions>

JSON Schema:
```json
[
  {
    "file": "path/to/file.py",
    "line": 42,
    "comment": "**[Priority: High - Component]** Synthesized, clear, and actionable feedback for the PR author."
  }
]
```
"""

def build_judge_prompt(
    review: str,
    security_findings: str,
    performance_findings: str,
    testing_findings: str,
    architecture_findings: str,
    documentation_findings: str,
    database_findings: str,
    accessibility_findings: str
) -> str:
    return f"""General Review:
{review}

Security Findings:
{security_findings}

Performance Findings:
{performance_findings}

Testing Findings:
{testing_findings}

Architecture Findings:
{architecture_findings}

Documentation Findings:
{documentation_findings}

Database Findings:
{database_findings}

Accessibility Findings:
{accessibility_findings}

Output your <thinking> block followed by the final deduplicated JSON array.
"""
