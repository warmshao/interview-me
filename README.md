# InterviewMe

> Distill your LLM conversations into a personal interview-prep knowledge base.

When you vibecode, analyze papers, or debug with an LLM, the conversation is full of valuable knowledge — and it evaporates the moment the session ends. **InterviewMe** automatically (or on demand) extracts **reusable knowledge** from those conversations, anonymizes it, organizes it into a browsable local website, and frames every page the way an interviewer would: study cards up top (definition / core concepts / comparison tables / diagrams / related links), high-frequency interview Q&A below (answers collapsed for self-testing, with follow-up probes).

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
4. Start a local server at **http://127.0.0.1:11123** (override with `--port`)

## Usage

| Mode | How it triggers |
|---|---|
| Automatic | When a Claude Code session ends, the hook filters out trivial sessions and extracts in the background |
| Manual | Type `/interview-me` in a conversation, optionally with a focus: `/interview-me only the RL parts, focus on PPO` |
| Review | Open http://127.0.0.1:11123 (or double-click `index.html` in the KB — data is inlined, works offline) |

Writing is **search-before-write**: existing pages get rewritten and merged; only genuinely new sub-domains get new pages. One HTML page = one coherent sub-domain (e.g. `kv-cache.html`), so page count stays under control. General categories (LLM / RL / WAM / VLA …) are created by the extracting model on demand — nothing is pre-seeded. Zero output is a valid outcome for conversations with nothing worth keeping.

## Two kinds of knowledge

- **General** — transferable concepts, anonymized, filed under self-organizing categories: `<kb>/<Category>/<sub-domain>.html`
- **Project** — tied to the project you were working on (architecture, trade-offs, pitfalls, "tell me about this project" interview angles): `<kb>/projects/<project>/<topic>.html`

The home page shows both as separate sections in the sidebar.

## From storing to learning

- **Spaced repetition** — every page carries a review record (stored in your browser, no backend). Intervals grow 1→3→7→14→30→60 days per successful recall; a lapse resets to day 1. New pages are due immediately. The sidebar's **Due for review** filter and the red dots on cards tell you what to revisit today.
- **🎯 Quiz me** — the home page embeds a bank of every interview Q&A from all pages. Quiz mode serves random questions (due pages weighted 3×), reveals the answer on demand, and your "Knew it / Didn't know" self-grade doubles as that page's review record. Scope the quiz to a category, a project, or due-only for targeted prep. Fully keyboard-driven: `space` reveal · `1` knew · `2` didn't · `→` next.
- **Learning dashboard** — streak counter, answers today/total, due count, and a GitHub-style activity heatmap keep the feedback loop alive.
- **Review anywhere** — mark a page reviewed from its card, from inside the page itself (floating ✓ button), or implicitly by grading it in quiz mode. Pages are print-friendly: printing expands all collapsed answers into a clean cheat-sheet.

## Rich content, offline

Pages support LaTeX math (`\( ... \)`, `$$ ... $$`), syntax-highlighted code snippets, and Markdown blocks — all rendered by vendored local assets (MathJax-SVG / highlight.js / marked), so everything works with zero network access.

## Knowledge base layout

```
~/.interview-me/
├── index.html               # home page (generated, data inlined, works offline)
├── index.json               # machine index for dedup decisions
├── config.json              # port etc.
├── .gitignore               # ignores everything, prevents accidental commits
├── LLM/  RL/  WAM/ ...      # general categories, created by the model on demand
│   └── kv-cache.html        # sub-domain page: study cards + interview Q&A
├── projects/
│   └── my-robot/            # project knowledge, one folder per project
│       └── vla-action-space.html
└── logs/                    # extraction prompts and logs
```

## Commands

```bash
python scripts/install.py                 # install
python scripts/install.py --startup       # install + auto-start server at logon
python scripts/install.py --uninstall     # uninstall (knowledge base is kept)
python scripts/serve.py start|stop|status # manage the local server
python scripts/build_index.py             # rebuild the home page manually
```

The server starts once at install time. To have it come back after every reboot, pass `--startup` (Windows: Task Scheduler logon task · macOS: LaunchAgent · Linux: systemd user unit). Claude Code and Codex share the same server instance — there is no conflict, `start` is idempotent.

## Codex users

The SessionEnd hook is a Claude Code feature. Under Codex, InterviewMe runs in manual-only mode — see [install.md](install.md).

## Design principles

- **Anonymized**: project names, paths, secrets and business data are stripped from general knowledge
- **Search before write**: dedup against the existing index; merge beats create
- **LLM never touches UI**: the model produces content only; the home page is generated deterministically by a script
- **Self-contained and offline**: every page has zero external dependencies; diagrams are inline SVG / pure CSS
- **Less is more**: skipping an empty conversation is correct behavior
