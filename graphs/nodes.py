import time

from configs.logger import get_logger
from tools.git.git_clone import GitCloneTool
from tools.github.github_client import GitHubClient
from tools.kitsune_engine import get_engine, namespace_for, set_active
from analysis.repo_analyzer import RepoAnalyzer
from analysis.repo_summary import RepoSummary
from agents.reviewer_agent import ReviewerAgent
from agents.security_agent import SecurityAgent
from agents.performance_agent import PerformanceAgent
from agents.testing_agent import TestingAgent
from agents.architecture_agent import ArchitectureAgent
from agents.judge_agent import JudgeAgent
from agents.fix_agent import FixAgent
from graphs.state import PipelineState

logger = get_logger(__name__)


def _engine_for(state: PipelineState):
    """The Kitsune engine (own index) for the repository in this pipeline run."""
    return get_engine(namespace_for(state["owner"], state["repo_name"]))

# Groq's free-tier TPM cap (8000 for plain chat models, confirmed live) is easy for a real
# diff + retrieved context to exceed on its own -- a single agent's prompt for a modest test
# PR already needed ~9182 tokens. Truncate both large text blobs once, at the source, rather
# than in each of the 8 agents separately.
_MAX_DIFF_CHARS = 4000
_MAX_CONTEXT_CHARS = 5000


def _join_until_budget(blocks: list[str], max_chars: int, label: str) -> str:
    """Concatenate blocks (one per changed file / one per retrieved chunk) up to a character
    budget WITHOUT ever cutting a single block mid-way. A flat text[:max_chars] slice can chop
    a file's diff off mid-function, and an LLM has no way to tell "ArchFox truncated this" from
    "this code is genuinely incomplete" -- it will (correctly, given what it's shown) flag the
    file as broken. Dropping whole blocks instead keeps every included file/chunk syntactically
    complete; the first block is always included in full even if it alone exceeds the budget,
    so a single large file still produces useful output instead of an empty diff.
    """
    result = ""
    omitted = 0
    for block in blocks:
        if result and len(result) + len(block) > max_chars:
            omitted += 1
            continue
        result += block

    if omitted:
        logger.warning(f"{label}: omitted {omitted} block(s) to stay within {max_chars} chars")
        result += f"\n\n... [TRUNCATED: {omitted} more section(s) omitted to fit the LLM's token budget]"

    return result


def clone_node(state: PipelineState) -> dict:
    repo_name = state["repo_url"].split("/")[-1].replace(".git", "")
    owner = state["repo_url"].rstrip("/").replace(".git", "").split("/")[-2]

    cloner = GitCloneTool()
    repo_path = cloner.clone_repo(state["repo_url"], repo_name)
    logger.info(f"Cloned repo to {repo_path}")

    return {"repo_path": repo_path, "repo_name": repo_name, "owner": owner}


def index_node(state: PipelineState) -> dict:
    logger.info("Kitsune is indexing the repository...")
    # Make this repo's engine the one the agents' graph tools query.
    engine = set_active(namespace_for(state["owner"], state["repo_name"]))
    metrics = engine.index_repository(state["repo_path"])  # incremental: unchanged files are skipped
    logger.info(metrics.summary())
    return {}


def architecture_node(state: PipelineState) -> dict:
    analyzer = RepoAnalyzer()
    architecture = analyzer.analyze(state["repo_path"])
    analyzer.save(architecture)
    logger.info("Architecture map created")
    return {"architecture": architecture}


def summary_node(state: PipelineState) -> dict:
    summary = RepoSummary().summarize(state["repo_path"])
    logger.info(f"Repository summary:\n{summary}")
    return {"summary": summary}


def fetch_pr_node(state: PipelineState) -> dict:
    github = GitHubClient()
    pr_files = github.get_pr_files(state["owner"], state["repo_name"], state["pr_number"])
    return {"pr_files": pr_files}


def build_diff_node(state: PipelineState) -> dict:
    file_blocks = []

    for file in state["pr_files"]:
        block = f"\nFILE: {file['filename']}\n"
        patch = file.get("patch")
        if patch:
            block += patch
        file_blocks.append(block)

    diff_content = _join_until_budget(file_blocks, _MAX_DIFF_CHARS, "diff_content")
    return {"diff_content": diff_content}


def retrieve_context_node(state: PipelineState) -> dict:
    logger.info("Kitsune is pulling context for the review...")
    engine = _engine_for(state)
    context_chunks = []

    for file in state["pr_files"]:
        query = file.get("patch") or file["filename"]
        # Hybrid search: meaning + keywords + call graph, within the context budget
        context = engine.search_semantic(query=query)
        context_chunks.append(context)

    retrieved_context = _join_until_budget(context_chunks, _MAX_CONTEXT_CHARS, "retrieved_context")
    return {"retrieved_context": retrieved_context}


# All 8 of these fan out from retrieve_context_node and run concurrently. Firing all 8 at
# once easily exceeds Groq's free-tier tokens-per-minute budget (as low as 8000 TPM), which
# manifests as intermittent 429/401 failures under load. Staggering their actual outbound
# requests spreads the burst without meaningfully hurting overall wall-clock time.
_STAGGER_SECONDS = {
    "review": 0, "security": 4, "performance": 8, "testing": 12,
    "architecture_review": 16, "documentation": 20, "database": 24, "accessibility": 28,
}


def review_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["review"])
    reviewer = ReviewerAgent()
    review = reviewer.review(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"review": review}


def security_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["security"])
    agent = SecurityAgent()
    security_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"security_findings": security_findings}


def performance_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["performance"])
    agent = PerformanceAgent()
    performance_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"performance_findings": performance_findings}


def testing_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["testing"])
    agent = TestingAgent()
    testing_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"testing_findings": testing_findings}


def architecture_review_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["architecture_review"])
    agent = ArchitectureAgent()
    architecture_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"architecture_findings": architecture_findings}


def documentation_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["documentation"])
    from agents.documentation_agent import DocumentationAgent
    agent = DocumentationAgent()
    documentation_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"documentation_findings": documentation_findings}


def database_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["database"])
    from agents.database_agent import DatabaseAgent
    agent = DatabaseAgent()
    database_findings = agent.review(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"database_findings": database_findings}


def accessibility_node(state: PipelineState) -> dict:
    time.sleep(_STAGGER_SECONDS["accessibility"])
    from agents.accessibility_agent import AccessibilityAgent
    agent = AccessibilityAgent()
    accessibility_findings = agent.review(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"accessibility_findings": accessibility_findings}


def judge_node(state: PipelineState) -> dict:
    agent = JudgeAgent()
    final_report = agent.judge(
        review=state["review"],
        security_findings=state["security_findings"],
        performance_findings=state["performance_findings"],
        testing_findings=state["testing_findings"],
        architecture_findings=state["architecture_findings"],
        documentation_findings=state.get("documentation_findings", "No documentation issues found."),
        database_findings=state.get("database_findings", "No database issues found."),
        accessibility_findings=state.get("accessibility_findings", "No accessibility issues found.")
    )
    return {"final_report": final_report}


def kitsune_fix_node(state: PipelineState) -> dict:
    import json
    import os
    import re

    logger.info("Kitsune is processing JSON findings to post inline comments...")

    try:
        report_text = state["final_report"].strip()

        # judge_prompt.py's system prompt (by design) has the model emit a <thinking> block
        # BEFORE the fenced JSON, so a fence is essentially never at the very start of the
        # string -- search for a ```json ... ``` block anywhere, don't assume position 0.
        fence_match = re.search(r"```json\s*(.*?)```", report_text, re.DOTALL)
        if not fence_match:
            fence_match = re.search(r"```\s*(.*?)```", report_text, re.DOTALL)

        if fence_match:
            report_text = fence_match.group(1).strip()
        else:
            # No fence at all -- fall back to the first top-level [...] array in the text.
            array_match = re.search(r"\[.*\]", report_text, re.DOTALL)
            if array_match:
                report_text = array_match.group(0)

        findings = json.loads(report_text)
    except Exception as e:
        logger.error(f"Failed to parse final_report as JSON: {e}")
        return {"fix_payload": str(e)}
        
    github_client = GitHubClient()
    pr_details = github_client.get_pr_details(state["owner"], state["repo_name"], state["pr_number"])
    commit_id = pr_details.get("head", {}).get("sha")
    
    if not commit_id:
        logger.error("Could not find commit_id for PR.")
        return {"fix_payload": "No commit ID found."}

    posted_count = 0
    general_comments = []

    for finding in findings:
        target_file = finding.get("file")
        target_line = finding.get("line")
        comment = finding.get("comment")
        
        if not target_file or not target_line or not comment:
            continue
            
        # Clean up path if it includes the clone prefix
        clone_prefix = os.path.join("data", "repos", state["repo_name"], "")
        clone_prefix_fwd = clone_prefix.replace("\\", "/")
        if clone_prefix in target_file:
            target_file = target_file.split(clone_prefix)[1]
        elif clone_prefix_fwd in target_file:
            target_file = target_file.split(clone_prefix_fwd)[1]
        target_file = target_file.replace("\\", "/")
        
        try:
            github_client.post_inline_pr_comment(
                state["owner"], state["repo_name"], state["pr_number"],
                commit_id, target_file, int(target_line), comment
            )
            posted_count += 1
        except Exception as e:
            logger.warning(f"Failed to post inline comment for {target_file}:{target_line}. {e}")
            general_comments.append(f"**{target_file}:{target_line}** - {comment}")
            
    if general_comments:
        fallback_body = "### General Findings\n" + "\n".join(f"- {c}" for c in general_comments)
        github_client.post_pr_comment(state["owner"], state["repo_name"], state["pr_number"], fallback_body)

    logger.info(f"Successfully posted {posted_count} inline comments to GitHub PR!")
    return {"fix_payload": json.dumps(findings, indent=2)}
