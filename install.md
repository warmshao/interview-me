# InterviewMe Installation

## Requirements

- Python 3.8+ (standard library only — nothing to pip install)
- Claude Code CLI (required for automatic hook mode; `claude` must be on PATH)
- Windows / macOS / Linux

## Install for Claude Code (recommended)

```bash
git clone https://github.com/warmshao/interview-me.git
cd interview-me
python scripts/install.py
```

What the installer does:

1. Copies `SKILL.md`, `prompts/`, `scripts/`, `templates/` to `~/.claude/skills/interview-me/`
2. Backs up `~/.claude/settings.json` to `settings.json.bak-interview-me`, then idempotently registers a SessionEnd hook
3. Initializes the knowledge base (default `~/.interview-me`): `.gitignore`, `index.json`, and the first `index.html`
4. Starts the local server in the background at `http://127.0.0.1:11123`

### Options

```bash
python scripts/install.py --kb D:\knowledge-base   # custom knowledge base directory
python scripts/install.py --port 12345             # custom port
python scripts/install.py --no-hook                # skip hook registration (manual mode only)
python scripts/install.py --no-server              # skip server startup
python scripts/install.py --uninstall              # uninstall (knowledge base is kept)
```

**Restart Claude Code** after installing so the hook takes effect.

### How the automatic mode works

When a Claude Code session ends, the hook (`scripts/hook_session_end.py`) reads the hook payload on stdin, skips trivial sessions (transcript < 8 KB or < 3 user messages), then spawns a detached headless `claude -p` process that follows `prompts/extract.md` to distill the conversation. It never blocks your session exit, and a recursion guard (`INTERVIEW_ME_EXTRACTING=1`) prevents extraction sessions from re-triggering the hook.

## Install for Codex (manual mode)

Codex has no SessionEnd hook, so extraction is manual-only:

1. Clone this repo to a permanent location, e.g. `~/interview-me`
2. Initialize the knowledge base and start the server:

   ```bash
   python scripts/build_index.py            # initialize the KB home page
   python scripts/serve.py start            # start http://127.0.0.1:11123
   ```

3. Append the contents of `prompts/extract.md` to Codex's global instructions (`~/.codex/AGENTS.md`), substituting the placeholders with real values:
   - `{{TRANSCRIPT_OR_CONTEXT}}` → "The full current conversation context"
   - `{{KB_DIR}}` → knowledge base path (default `~/.interview-me`)
   - `{{SKILL_DIR}}` → the repo clone path
   - `{{PROJECT_DIR}}` → ask the user / current working directory
   - `{{USER_REQUIREMENTS}}` → provided by the user in conversation
4. After a worthwhile conversation, tell Codex: "extract the knowledge from this conversation per the extract instructions".

## Verify the install

```bash
python scripts/serve.py status      # expect: running: http://127.0.0.1:11123
```

Open that URL in a browser — you should see an empty knowledge base home page. Then have a technical conversation with Claude and type `/interview-me`; you should see pages created and clickable URLs printed.

## Troubleshooting

**Server won't start / port already in use?**
`python scripts/serve.py stop`, then restart on another port: `python scripts/serve.py start --port 12345`. The port persists in the KB's `config.json`.

**Hook not firing?**
Make sure `claude` is on PATH and you restarted Claude Code after install. Check the KB's `logs/` directory for `extract-*.log`. Note the hook intentionally skips short sessions (transcript < 8 KB or < 3 user messages).

**Upgrading the skill?**
Just re-run `python scripts/install.py` — it is idempotent; your knowledge base and port config are preserved.

**Moving the knowledge base?**
`python scripts/install.py --kb <new-path>`, or set the `INTERVIEW_ME_KB` environment variable (highest priority, respected by every script).
