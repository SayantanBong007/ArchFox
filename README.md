# ArchFox 🦊

ArchFox is a Repository Knowledge Base System.

It analyzes your entire codebase to understand the deep relationships between your functions and classes to act as a powerful code reviewer.

## How to use ArchFox in your repository (GitHub Action)

You don't need to install anything! ArchFox is available as a plug-and-play **GitHub Action**.

Just add the following workflow file to your repository at `.github/workflows/archfox.yml`:

```yaml
name: ArchFox PR Review

on:
  pull_request:
    types: [opened, synchronize]
  issue_comment:
    types: [created]

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
          api_key: ${{ secrets.API_KEY }}
```

### Required Secrets
Make sure you have added the following to your repository's **Settings > Secrets and variables > Actions**:
- `API_KEY`: Your API key to run the AI models.
- `GITHUB_TOKEN`: This is automatically provided by GitHub Actions!

## Features
- **Cross-Language**: Fully supports Python, JavaScript, TypeScript, C, C++, Go, Java, and Rust via Tree-sitter!
- **Pinpoint Inline Comments**: ArchFox leaves exact line-by-line comments on your PR diffs.
- **Interactive Bot**: Reply to ArchFox's comments with `@archfox` to ask follow-up questions!

## 💬 Chat Feature

ArchFox includes a powerful **Chat Agent** that allows you to have a conversation directly with your codebase! 

Using the underlying **Kitsune Knowledge Engine**, the Chat Feature can:
- Answer complex questions about your repository architecture.
- Fetch code context automatically using hybrid (semantic + graph) search.
- Explain functions, trace dependencies, and clarify PR diffs in a conversational manner.

Whether you're interacting via the GitHub PR comments (using `@archfox`) or querying the backend locally, ArchFox provides a seamless conversational interface to help you understand your code faster.

### How to use the Chat Feature

There is no extra setup required! If you have installed the ArchFox GitHub Action, the bot is automatically available in your repository.

To use it:
1. Go to any Pull Request in your repository.
2. Leave a comment tagging `@archfox`, followed by your question.
   **Example:** `@archfox Why did we change the database schema here?`
3. ArchFox will automatically analyze the codebase context and reply directly in the thread!
