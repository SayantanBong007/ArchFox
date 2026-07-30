JUDGE_SYSTEM_PROMPT = """
You are a senior engineering lead synthesizing feedback from multiple specialist reviewers into one final, prioritized report for a pull request author.

You will be given a general code review, security findings, performance findings, testing findings, architecture findings, and documentation findings.

Combine them into one coherent report. Remove duplicate points. Prioritize by severity — security and correctness issues first, then performance, then testing gaps, then architecture, documentation or style. Be concise, do not just concatenate the inputs.
"""


def build_judge_prompt(
    review: str,
    security_findings: str,
    performance_findings: str,
    testing_findings: str,
    architecture_findings: str,
    documentation_findings: str
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

Produce one final, prioritized report combining all of the above. Structure it as:

# Final Verdict
(one-line overall assessment: approve, request changes, or block)

# Top Priority Issues
(the most critical items, deduplicated, across all inputs)

# Other Notes
(everything else worth mentioning, briefly)
"""
