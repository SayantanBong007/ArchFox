# ArchFox 🦊 AI Code Reviewer

ArchFox is a state-of-the-art AI pair programmer that reviews your Pull Requests using a hybrid **GraphRAG** Knowledge Engine (Neo4j & ChromaDB).

It analyzes your entire codebase to understand the deep relationships between your functions and classes before making suggestions!

## How to use ArchFox in your repository (GitHub Action)

You don't need to install anything! ArchFox is available as a plug-and-play **GitHub Action**.

Just add the following workflow file to your repository at `.github/workflows/archfox.yml`:

```yaml
name: ArchFox PR Review

on:
  pull_request:
    types: [opened, synchronize]

permissions:
  pull-requests: write
  contents: read

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code
        uses: actions/checkout@v4
        
      - name: Run ArchFox
        uses: SayantanBong007/ArchFox@master
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
          groq_api_key: ${{ secrets.GROQ_API_KEY }}
```

### Required Secrets
Make sure you have added the following to your repository's **Settings > Secrets and variables > Actions**:
- `GROQ_API_KEY`: Your API key from Groq to run the AI models.
- `GITHUB_TOKEN`: This is automatically provided by GitHub Actions!

## Features
- **Cross-Language**: Fully supports Python, JavaScript, and TypeScript via Tree-sitter!
- **Pinpoint Inline Comments**: ArchFox leaves exact line-by-line comments on your PR diffs.
- **Interactive Bot**: Reply to ArchFox's comments with `@archfox` to ask follow-up questions!
