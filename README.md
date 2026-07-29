# ArchFox

CLI-based code review agent with GitHub integration.

## Structure

- `apps/cli` — command-line entrypoint
- `agents/reviewer` — the review agent
- `tools/github` — GitHub API client
- `prompts` — prompt templates
- `configs` — settings and configuration
- `tests` — test suite

## Setup

```bash
pip install -e .
cp .env.example .env  # fill in required values
```

## Usage

```bash
archfox review <pr-url>
```
