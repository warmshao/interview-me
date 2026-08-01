#!/usr/bin/env python3
"""InterviewMe - SessionEnd hook for Claude Code.

Invoked by Claude Code when a session ends (hook JSON arrives on stdin).
Applies cheap filters, then spawns a detached headless `claude -p` process
to perform knowledge extraction. Exits immediately; never blocks the session.

Recursion guard: the spawned extraction process gets INTERVIEW_ME_EXTRACTING=1
in its environment, so when THAT session ends this hook exits right away.
"""
import json
import os
import shutil
import subprocess
import sys

MIN_BYTES = 8000        # transcripts smaller than this are not worth extracting
MIN_USER_MSGS = 3       # fewer user messages than this -> skip
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_KB = os.path.join(os.path.expanduser("~"), ".interview-me")


def find_claude_cmd():
    """Locate the claude CLI. On Windows `claude` is a .cmd wrapper whose
    detached launch produces no output, so prefer the native claude.exe
    shipped inside the npm package."""
    which = shutil.which("claude")
    if not which:
        return None
    if os.name == "nt":
        exe = os.path.join(os.path.dirname(which), "node_modules",
                           "@anthropic-ai", "claude-code", "bin", "claude.exe")
        if os.path.exists(exe):
            return [exe]
        return ["cmd", "/c", which]
    return [which]


def main():
    if os.environ.get("INTERVIEW_ME_EXTRACTING"):
        return  # recursion guard: this session IS an extraction run

    try:
        hook = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    transcript = hook.get("transcript_path", "")
    if not transcript or not os.path.exists(transcript):
        return
    if os.path.getsize(transcript) < MIN_BYTES:
        return

    # cheap signal: count user messages in the JSONL transcript
    user_msgs = 0
    try:
        with open(transcript, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                if '"type":"user"' in line or '"type": "user"' in line:
                    user_msgs += 1
                    if user_msgs >= MIN_USER_MSGS:
                        break
    except OSError:
        return
    if user_msgs < MIN_USER_MSGS:
        return

    kb = os.environ.get("INTERVIEW_ME_KB", DEFAULT_KB)
    os.makedirs(os.path.join(kb, "logs"), exist_ok=True)

    # assemble the extraction prompt (written to a file to avoid
    # command-line length limits) with runtime values substituted
    with open(os.path.join(SKILL_DIR, "prompts", "extract.md"),
              "r", encoding="utf-8") as f:
        extract = f.read()
    prompt = (extract
              .replace("{{TRANSCRIPT_OR_CONTEXT}}",
                       f"Transcript file: {transcript} "
                       f"(JSONL format; read it with Read/Grep)")
              .replace("{{KB_DIR}}", kb)
              .replace("{{SKILL_DIR}}", SKILL_DIR)
              .replace("{{PROJECT_DIR}}", hook.get("cwd", "") or "unknown")
              .replace("{{USER_REQUIREMENTS}}",
                       "None (automatic mode; decide the focus yourself)"))
    session_id = hook.get("session_id", "unknown")
    prompt_file = os.path.join(kb, "logs", f"extract-{session_id}.md")
    with open(prompt_file, "w", encoding="utf-8") as f:
        f.write(prompt)

    env = dict(os.environ, INTERVIEW_ME_EXTRACTING="1")
    log = open(os.path.join(kb, "logs", f"extract-{session_id}.log"),
               "a", encoding="utf-8")
    kwargs = dict(stdout=log, stderr=log, stdin=subprocess.DEVNULL,
                  env=env, close_fds=True, cwd=kb)
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS
                                   | subprocess.CREATE_NEW_PROCESS_GROUP
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kwargs["start_new_session"] = True

    claude_cmd = find_claude_cmd()
    if not claude_cmd:
        return  # no claude CLI available; fail silently
    args = claude_cmd + [
        "-p", f"Read {prompt_file} and follow its instructions exactly "
              f"to perform the knowledge extraction task.",
        "--allowedTools", "Read Write Edit Glob Grep Bash"]
    try:
        subprocess.Popen(args, **kwargs)
    except OSError:
        pass  # a hook must never surface errors


if __name__ == "__main__":
    main()
