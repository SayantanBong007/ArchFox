from configs.logger import get_logger
from tools.git.git_clone import GitCloneTool
from tools.github.github_client import GitHubClient
from kitsune.engine.knowledge_engine import RepositoryKnowledgeEngine
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

_engine = RepositoryKnowledgeEngine()


def clone_node(state: PipelineState) -> dict:
    repo_name = state["repo_url"].split("/")[-1].replace(".git", "")
    owner = state["repo_url"].rstrip("/").replace(".git", "").split("/")[-2]

    cloner = GitCloneTool()
    repo_path = cloner.clone_repo(state["repo_url"], repo_name)
    logger.info(f"Cloned repo to {repo_path}")

    return {"repo_path": repo_path, "repo_name": repo_name, "owner": owner}


def index_node(state: PipelineState) -> dict:
    logger.info("Kitsune RKE is indexing the repository...")
    _engine.index_repository(state["repo_path"])
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
    diff_content = ""

    for file in state["pr_files"]:
        diff_content += f"\nFILE: {file['filename']}\n"
        patch = file.get("patch")
        if patch:
            diff_content += patch

    return {"diff_content": diff_content}


def retrieve_context_node(state: PipelineState) -> dict:
    logger.info("Kitsune RKE is pulling context for the review...")
    context_chunks = []

    for file in state["pr_files"]:
        query = file.get("patch") or file["filename"]
        # Use semantic search + graph topological data
        context = _engine.search_semantic(query=query)
        context_chunks.append(context)

    return {"retrieved_context": "\n\n".join(context_chunks)}


def review_node(state: PipelineState) -> dict:
    reviewer = ReviewerAgent()
    review = reviewer.review(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"review": review}


def security_node(state: PipelineState) -> dict:
    agent = SecurityAgent()
    security_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"security_findings": security_findings}


def performance_node(state: PipelineState) -> dict:
    agent = PerformanceAgent()
    performance_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"performance_findings": performance_findings}


def testing_node(state: PipelineState) -> dict:
    agent = TestingAgent()
    testing_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"testing_findings": testing_findings}


def architecture_review_node(state: PipelineState) -> dict:
    agent = ArchitectureAgent()
    architecture_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"architecture_findings": architecture_findings}


def documentation_node(state: PipelineState) -> dict:
    from agents.documentation_agent import DocumentationAgent
    agent = DocumentationAgent()
    documentation_findings = agent.analyze(
        diff_content=state["diff_content"],
        repo_context=state["retrieved_context"]
    )
    return {"documentation_findings": documentation_findings}


def judge_node(state: PipelineState) -> dict:
    agent = JudgeAgent()
    final_report = agent.judge(
        review=state["review"],
        security_findings=state["security_findings"],
        performance_findings=state["performance_findings"],
        testing_findings=state["testing_findings"],
        architecture_findings=state["architecture_findings"],
        documentation_findings=state.get("documentation_findings", "No documentation issues found.")
    )
    return {"final_report": final_report}


def kitsune_fix_node(state: PipelineState) -> dict:
    import json
    import os
    
    logger.info("Kitsune is processing JSON findings to post inline comments...")
    
    try:
        report_text = state["final_report"].strip()
        if report_text.startswith("```json"):
            report_text = report_text[7:]
        elif report_text.startswith("```"):
            report_text = report_text[3:]
        if report_text.endswith("```"):
            report_text = report_text[:-3]
        report_text = report_text.strip()
        
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
