# Agent rules

See [CLAUDE.md](./CLAUDE.md) — the canonical operating rules for this repository.

## Authorship
- **Author (docs + commits):** {{AUTHOR_NAME}} <{{AUTHOR_EMAIL}}>. Use this identity for git commits (`git config user.name`/`user.email`) and for the `author:` field in generated docs. Do not change it unless the user says so.
- **LLM co-authorship:** {{COAUTHOR_POLICY}}. Default is **none** — commits carry NO `Co-Authored-By` trailer. Only add one (for the model/provider actually used: anthropic / openai / deepseek / minimax / …) if this line enables it or the user explicitly asks.
