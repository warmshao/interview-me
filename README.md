# InterviewMe

> Distill your LLM conversations — and your job descriptions — into a personal interview-prep knowledge base.

[English](README.md) | [中文](README_zh.md)

When you vibecode, analyze papers, or debug with an LLM, the conversation is full of valuable knowledge — and it evaporates the moment the session ends. **InterviewMe** captures it automatically (or on demand), anonymizes it, and organizes it into a browsable local website where every page is built the way an interviewer thinks: study cards up top (definition / core concepts / comparison tables / diagrams / related links), high-frequency Q&A below (answers collapsed for self-testing, with follow-up probes).

**Built for humans to review and prepare — not an AI-facing wiki.**

## Quick install

Paste this into Claude Code or Codex:

```
Install interview-me from https://github.com/warmshao/interview-me:
clone the repo, then run `python scripts/install.py`.
Follow install.md if anything fails.
```

The installer will:

1. Install the skill to `~/.claude/skills/interview-me/`
2. Idempotently register a SessionEnd hook in `~/.claude/settings.json` (backing up the original)
3. Initialize the knowledge base (default `~/.interview-me`, override with `--kb`)
4. Start a local server at **http://127.0.0.1:11123** (override with `--port`, `--startup` for boot auto-start)

## Two ways to fill your knowledge base

| Mode | How it works |
|---|---|
| **Conversation distillation** | Automatic: a SessionEnd hook filters out trivial sessions and extracts in the background. Manual: type `/interview-me` mid-chat, optionally with a focus (`/interview-me only the RL parts`) |
| **JD / interview prep** | Paste a job description or real interview questions: `/interview-me <paste JD here>`. It decomposes the JD into ranked topics, researches answers on the web, writes/merges knowledge pages per topic, and builds a **prep roadmap** page with a study order and mock-interview Q&A |

Writing is **search-before-write**: existing pages get rewritten and merged; only genuinely new sub-domains get new pages. One HTML page = one coherent sub-domain (e.g. `kv-cache.html`), so page count stays under control. General categories (LLM / RL / WAM / VLA …) are created by the extracting model on demand. Zero output is a valid outcome for conversations with nothing worth keeping.

## Two kinds of knowledge

- **General** — transferable concepts, anonymized, filed under self-organizing categories: `<kb>/<Category>/<sub-domain>.html`
- **Project** — tied to the project you were working on (architecture, trade-offs, pitfalls, "tell me about this project" angles): `<kb>/projects/<project>/<topic>.html`. JD prep roadmaps live here too (`projects/jd-<role>/`)

The home page shows both as separate sections in the sidebar.

## From storing to learning

- **Spaced repetition** — every page carries a review record (stored in your browser, no backend). Intervals grow 1→3→7→14→30→60 days per successful recall; a lapse resets to day 1. New pages are due immediately. The sidebar's **Due for review** filter and the red dots on cards tell you what to revisit today.
- **🎯 Quiz me** — the home page embeds a bank of every interview Q&A from all pages. Random questions (due pages weighted 3×), answer reveal on demand, and your "Knew it / Didn't know" self-grade doubles as the page's review record. Scope to a category, a project, or due-only. Fully keyboard-driven: `space` · `1` · `2` · `→`.
- **Learning dashboard** — streak counter, answers today/total, due count, and a GitHub-style activity heatmap.
- **Review anywhere** — mark reviewed from a card, from the floating button inside a page, or implicitly by grading in quiz mode. Pages are print-friendly: printing expands all collapsed answers into a clean cheat-sheet.

## Manage from the browser

- **Delete a page** — hover a card, click ✕, confirm. The server removes the file and rebuilds the catalog.
- **Blocked topics** — the 🏷 Filters button opens a tag editor; blocked domains are injected into the extraction prompt so future conversations skip them.
- **Light / dark theme** — synced across every page.

## Rich content, offline

Pages support LaTeX math (`\( ... \)`, `$$ ... $$`), syntax-highlighted code, and Markdown blocks — all rendered by vendored local assets (MathJax-SVG with full TeX extensions / highlight.js / marked), so everything works with zero network access.

## Knowledge base layout

```
~/.interview-me/
├── index.html               # home page (generated, data inlined, works offline)
├── index.json               # machine index for dedup decisions
├── config.json              # port, blocked topics
├── assets/                  # vendored JS/CSS (math, highlighting, markdown)
├── LLM/  RL/  WAM/ ...      # general categories, created by the model on demand
│   └── kv-cache.html        # sub-domain page: study cards + interview Q&A
├── projects/
│   ├── my-robot/            # project knowledge, one folder per project
│   └── jd-some-role/        # JD prep roadmap
└── logs/                    # extraction prompts and logs
```

## Commands

```bash
python scripts/install.py                 # install / upgrade (idempotent)
python scripts/install.py --startup       # install + auto-start server at logon
python scripts/install.py --uninstall     # uninstall (knowledge base is kept)
python scripts/serve.py start|stop|status # manage the local server
python scripts/build_index.py             # rebuild the home page manually
```

Claude Code and Codex share the same server instance — no conflict, `start` is idempotent. Codex has no SessionEnd hook, so extraction there is manual-only — see [install.md](install.md).

## Design principles

- **Anonymized**: project names, paths, secrets and business data are stripped from general knowledge
- **Search before write**: dedup against the existing index; merge beats create
- **LLM never touches UI**: the model produces content only; the home page is generated deterministically by a script
- **Self-contained and offline**: every page has zero external dependencies
- **Less is more**: skipping an empty conversation is correct behavior

## License

[MIT](LICENSE)
