#!/usr/bin/env python3
"""InterviewMe - installer.

Usage:
  python install.py                      install for Claude Code (default KB: ~/.interview-me)
  python install.py --kb D:\\knowledge    custom knowledge base location
  python install.py --port 12345         custom local server port
  python install.py --no-server          do not start the local server
  python install.py --no-hook            do not register the SessionEnd hook (manual mode only)
  python install.py --uninstall          remove skill + hook (keeps the knowledge base)

What it does:
  1. Copy SKILL.md / prompts / scripts / templates to ~/.claude/skills/interview-me/
  2. Idempotently register a SessionEnd hook in ~/.claude/settings.json (with backup)
  3. Initialize the knowledge base and generate the first index.html
  4. Start the local server at http://127.0.0.1:<port>
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

REPO_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CLAUDE_DIR = os.path.join(os.path.expanduser("~"), ".claude")
SKILL_DST = os.path.join(CLAUDE_DIR, "skills", "interview-me")
SETTINGS = os.path.join(CLAUDE_DIR, "settings.json")
DEFAULT_KB = os.path.join(os.path.expanduser("~"), ".interview-me")
COPY_ITEMS = ["SKILL.md", "prompts", "scripts", "templates", "assets"]


def copy_skill():
    os.makedirs(SKILL_DST, exist_ok=True)
    for item in COPY_ITEMS:
        src = os.path.join(REPO_DIR, item)
        dst = os.path.join(SKILL_DST, item)
        if os.path.isdir(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)
    print(f"[1/4] skill installed to {SKILL_DST}")


def register_hook():
    os.makedirs(CLAUDE_DIR, exist_ok=True)
    settings = {}
    if os.path.exists(SETTINGS):
        with open(SETTINGS, "r", encoding="utf-8") as f:
            settings = json.load(f)
        shutil.copy2(SETTINGS, SETTINGS + ".bak-interview-me")

    hook_script = os.path.join(SKILL_DST, "scripts", "hook_session_end.py")
    command = f'"{sys.executable}" "{hook_script}"'

    hooks = settings.setdefault("hooks", {})
    session_end = hooks.setdefault("SessionEnd", [])
    for group in session_end:
        for h in group.get("hooks", []):
            if "hook_session_end.py" in h.get("command", ""):
                h["command"] = command  # already registered -> refresh path
                with open(SETTINGS, "w", encoding="utf-8") as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                print("[2/4] SessionEnd hook already present, path refreshed")
                return
    session_end.append({"hooks": [{"type": "command", "command": command}]})
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print("[2/4] SessionEnd hook registered in settings.json")


def unregister_hook():
    if not os.path.exists(SETTINGS):
        return
    with open(SETTINGS, "r", encoding="utf-8") as f:
        settings = json.load(f)
    shutil.copy2(SETTINGS, SETTINGS + ".bak-interview-me")
    session_end = settings.get("hooks", {}).get("SessionEnd", [])
    for group in list(session_end):
        group["hooks"] = [h for h in group.get("hooks", [])
                          if "hook_session_end.py" not in h.get("command", "")]
    session_end[:] = [g for g in session_end if g.get("hooks")]
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print("[uninstall] SessionEnd hook removed")


def init_kb(kb: str):
    os.makedirs(kb, exist_ok=True)
    gitignore = os.path.join(kb, ".gitignore")
    if not os.path.exists(gitignore):
        with open(gitignore, "w") as f:
            f.write("*\n")
    index_json = os.path.join(kb, "index.json")
    if not os.path.exists(index_json):
        with open(index_json, "w", encoding="utf-8") as f:
            json.dump({"knowledge": []}, f, ensure_ascii=False, indent=2)
    subprocess.run([sys.executable,
                    os.path.join(REPO_DIR, "scripts", "build_index.py"),
                    "--kb", kb], check=True)
    print(f"[3/4] knowledge base initialized: {kb}")


def start_server(kb: str, port: int):
    subprocess.run([sys.executable,
                    os.path.join(REPO_DIR, "scripts", "serve.py"),
                    "start", "--kb", kb, "--port", str(port)], check=True)
    print(f"[4/4] open http://127.0.0.1:{port} in your browser")


def uninstall():
    unregister_hook()
    if os.path.exists(SKILL_DST):
        shutil.rmtree(SKILL_DST)
        print(f"[uninstall] skill directory removed: {SKILL_DST}")
    print("[uninstall] done. The knowledge base was left untouched; "
          "delete it manually if desired.")


def main():
    ap = argparse.ArgumentParser(description="InterviewMe installer")
    ap.add_argument("--kb", default=os.environ.get("INTERVIEW_ME_KB", DEFAULT_KB),
                    help="knowledge base directory (default ~/.interview-me)")
    ap.add_argument("--port", type=int, default=11123, help="local server port")
    ap.add_argument("--no-server", action="store_true",
                    help="do not start the local server")
    ap.add_argument("--no-hook", action="store_true",
                    help="do not register the SessionEnd hook")
    ap.add_argument("--uninstall", action="store_true", help="uninstall")
    args = ap.parse_args()

    if args.uninstall:
        uninstall()
        return

    kb = os.path.abspath(args.kb)
    copy_skill()
    if args.no_hook:
        print("[2/4] hook registration skipped (--no-hook); "
              "manual /interview-me mode only")
    else:
        register_hook()
    init_kb(kb)
    if args.no_server:
        print(f"[4/4] server start skipped (--no-server); later run: "
              f"python {os.path.join(SKILL_DST, 'scripts', 'serve.py')} start")
    else:
        start_server(kb, args.port)

    print("\nDone! How to use:")
    print("  automatic: knowledge is extracted when a Claude Code session ends")
    print("  manual:    type /interview-me [optional focus instructions]")
    print(f"  website:   http://127.0.0.1:{args.port}")


if __name__ == "__main__":
    main()
