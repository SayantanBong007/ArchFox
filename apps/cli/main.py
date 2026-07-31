"""
ArchFox CLI — Run the full PR review pipeline from the command line.

Usage:
    python apps/cli/main.py --repo https://github.com/owner/repo --pr 2
"""
import sys
import os

# Walk up 3 levels: apps/cli/main.py → apps/cli → apps → ArchFox root
# This lets Python find modules like 'graphs', 'agents', 'configs' etc.
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

import typer
import os
import shutil
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

from configs.logger import setup_logging, get_logger
setup_logging()
logger = get_logger(__name__)

from graphs.pipeline_graph import build_pipeline_graph

app = typer.Typer(
    help="ArchFox 🦊 AI Code Reviewer & Repository Knowledge Engine.",
    no_args_is_help=True
)
console = Console()


@app.command()
def init():
    """Scaffold ArchFox in your repository (Interactive Wizard)."""
    console.print(Panel.fit("[bold magenta]🦊 Welcome to the ArchFox Setup Wizard![/bold magenta]"))
    
    groq_key = Prompt.ask("Enter your [bold cyan]GROQ_API_KEY[/bold cyan]", password=True)
    github_token = Prompt.ask("Enter your [bold cyan]GITHUB_TOKEN[/bold cyan] (for PR comments)", password=True)
    
    # 1. Write .env
    env_content = f"GROQ_API_KEY={groq_key}\nGITHUB_TOKEN={github_token}\n"
    with open(".env", "w") as f:
        f.write(env_content)
    console.print("[green]✔ Created .env file locally.[/green]")
    
    # 2. Write GitHub Action
    workflow_dir = Path(".github/workflows")
    workflow_dir.mkdir(parents=True, exist_ok=True)
    
    template_path = Path(__file__).parent.parent.parent / "configs" / "archfox_action_template.yml"
    target_path = workflow_dir / "archfox.yml"
    
    if template_path.exists():
        shutil.copy(template_path, target_path)
        console.print("[green]✔ Created .github/workflows/archfox.yml[/green]")
    else:
        console.print(f"[red]Error: Could not find template at {template_path}[/red]")
        return
        
    success_msg = """
[bold green]ArchFox is ready! 🦊[/bold green]

To activate it:
1. Make sure you add GROQ_API_KEY and GITHUB_TOKEN to your repository's GitHub Secrets.
2. Commit and push the new `.github/workflows/archfox.yml` file.

ArchFox will now automatically review all new Pull Requests!
    """
    console.print(Panel(success_msg, border_style="green"))


@app.command()
def review(
    repo: str = typer.Option(..., help="Full GitHub repo URL (e.g., https://github.com/owner/repo)"),
    pr: int = typer.Option(..., help="PR number to review")
):
    """Run the ArchFox AI PR review pipeline."""
    console.print(Panel.fit(f"[bold blue]ArchFox[/bold blue] starting — repo: [cyan]{repo}[/cyan]  PR: [cyan]#{pr}[/cyan]"))

    graph = build_pipeline_graph()
    
    with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), console=console) as progress:
        progress.add_task(description="Running Pipeline Graph...", total=None)
        result = graph.invoke({"repo_url": repo, "pr_number": pr})

    sections = [
        ("REVIEW",                "review"),
        ("SECURITY FINDINGS",     "security_findings"),
        ("PERFORMANCE FINDINGS",  "performance_findings"),
        ("TESTING FINDINGS",      "testing_findings"),
        ("ARCHITECTURE FINDINGS", "architecture_findings"),
        ("DOCUMENTATION FINDINGS","documentation_findings"),
        ("FINAL REPORT (Judge)",  "final_report"),
        ("KITSUNE FIX PAYLOAD",   "fix_payload"),
    ]
    for title, key in sections:
        value = result.get(key, "No output.")
        console.print(Panel(str(value), title=f"[bold green]{title}[/bold green]", border_style="green"))

    # ---------------------------------------------------------
    # POST TO GITHUB
    # ---------------------------------------------------------
    try:
        repo_parts = repo.rstrip("/").split("/")
        repo_name = repo_parts[-1]
        owner = repo_parts[-2]
        
        comment_body = f"# 🦊 ArchFox AI Code Review\n\n"
        if "final_report" in result:
            comment_body += f"{result['final_report']}\n\n"
            
        if "fix_payload" in result:
            comment_body += "---\n### 🛠️ Suggested Fixes\n\n"
            comment_body += f"{result['fix_payload']}\n"

        from tools.github.github_client import GitHubClient
        client = GitHubClient()
        client.post_pr_comment(owner, repo_name, pr, comment_body)
        console.print("[bold green]Successfully posted review to GitHub PR![/bold green]")
    except Exception as e:
        console.print(f"[bold red]Failed to post to GitHub: {e}[/bold red]")

    console.print("[bold blue]ArchFox run complete. 🦊[/bold blue]")


if __name__ == "__main__":
    app()

