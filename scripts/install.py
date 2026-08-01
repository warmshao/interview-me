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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from kbutil import write_pointer, remove_pointer

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
    write_pointer(kb)  # so hook/serve/build resolve the same KB everywhere
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


STARTUP_NAME = "InterviewMe"


def register_startup(kb: str, port: int):
    """Start the local server automatically at logon/boot. Uses the INSTALLED
    copy of serve.py (under ~/.claude/skills) so it survives repo deletion."""
    serve = os.path.join(SKILL_DST, "scripts", "serve.py")
    if os.name == "nt":
        cmd = f'"{sys.executable}" "{serve}" start --kb "{kb}" --port {port}'
        subprocess.run(["schtasks", "/create", "/f", "/tn", STARTUP_NAME,
                        "/sc", "onlogon", "/tr", cmd], check=True,
                       capture_output=True)
        print("[startup] registered a logon task (Task Scheduler: InterviewMe)")
    elif sys.platform == "darwin":
        agents = os.path.expanduser("~/Library/LaunchAgents")
        os.makedirs(agents, exist_ok=True)
        plist = os.path.join(agents, "com.interviewme.serve.plist")
        with open(plist, "w") as f:
            f.write(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.interviewme.serve</string>
  <key>ProgramArguments</key><array>
    <string>{sys.executable}</string><string>{serve}</string>
    <string>start</string><string>--kb</string><string>{kb}</string>
    <string>--port</string><string>{port}</string>
  </array>
  <key>RunAtLoad</key><true/>
</dict></plist>""")
        subprocess.run(["launchctl", "load", plist], capture_output=True)
        print(f"[startup] registered a LaunchAgent: {plist}")
    else:
        unit_dir = os.path.expanduser("~/.config/systemd/user")
        os.makedirs(unit_dir, exist_ok=True)
        unit = os.path.join(unit_dir, "interview-me.service")
        with open(unit, "w") as f:
            f.write(f"""[Unit]
Description=InterviewMe knowledge base server

[Service]
ExecStart={sys.executable} {serve} start --kb {kb} --port {port}

[Install]
WantedBy=default.target
""")
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True)
        subprocess.run(["systemctl", "--user", "enable", "interview-me.service"],
                       capture_output=True)
        print("[startup] registered a systemd user unit; to survive logout run: "
              "loginctl enable-linger $USER")


def unregister_startup():
    if os.name == "nt":
        subprocess.run(["schtasks", "/delete", "/f", "/tn", STARTUP_NAME],
                       capture_output=True)
        print("[uninstall] logon task removed")
    elif sys.platform == "darwin":
        plist = os.path.expanduser(
            "~/Library/LaunchAgents/com.interviewme.serve.plist")
        if os.path.exists(plist):
            subprocess.run(["launchctl", "unload", plist], capture_output=True)
            os.remove(plist)
            print("[uninstall] LaunchAgent removed")
    else:
        unit = os.path.expanduser("~/.config/systemd/user/interview-me.service")
        if os.path.exists(unit):
            subprocess.run(["systemctl", "--user", "disable",
                            "interview-me.service"], capture_output=True)
            os.remove(unit)
            print("[uninstall] systemd user unit removed")


def uninstall():
    unregister_startup()
    unregister_hook()
    remove_pointer()
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
    ap.add_argument("--startup", action="store_true",
                    help="auto-start the local server at logon/boot")
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
    if args.startup:
        register_startup(kb, args.port)

    print("\nDone! How to use:")
    print("  automatic: knowledge is extracted when a Claude Code session ends")
    print("  manual:    type /interview-me [optional focus instructions]")
    print(f"  website:   http://127.0.0.1:{args.port}")


if __name__ == "__main__":
    main()
