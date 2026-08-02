from typing import TypedDict


class PipelineState(TypedDict):
    repo_url: str
    pr_number: int
    owner: str
    repo_name: str
    repo_path: str
    pr_files: list
    diff_content: str
    architecture: dict
    summary: str
    retrieved_context: str
    review: str
    security_findings: str
    performance_findings: str
    testing_findings: str
    architecture_findings: str
    documentation_findings: str
    database_findings: str
    accessibility_findings: str
    final_report: str
    fix_payload: str
