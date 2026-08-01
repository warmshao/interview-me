#!/usr/bin/env python3
"""InterviewMe - local knowledge base server.

Usage:
  python serve.py run [--kb KB] [--port PORT]    foreground (debugging)
  python serve.py start [--kb KB] [--port PORT]  detached background (default)
  python serve.py stop [--kb KB]
  python serve.py status [--kb KB]

Default address: http://127.0.0.1:11123
Port persists in <kb>/config.json; PID file at <kb>/.server.pid.
"""
import argparse
import http.server
import json
import os
import signal
import subprocess
import sys

DEFAULT_PORT = 11123
DEFAULT_KB = os.path.join(os.path.expanduser("~"), ".interview-me")


def kb_default() -> str:
    return os.environ.get("INTERVIEW_ME_KB", DEFAULT_KB)


def paths(kb: str) -> dict:
    return {
        "config": os.path.join(kb, "config.json"),
        "pid": os.path.join(kb, ".server.pid"),
        "log": os.path.join(kb, ".server.log"),
    }


def load_config(kb: str) -> dict:
    cfg_path = paths(kb)["config"]
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(kb: str, cfg: dict):
    with open(paths(kb)["config"], "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


def pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        r = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
            capture_output=True, text=True)
        return str(pid) in r.stdout
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def read_pid(kb: str):
    try:
        with open(paths(kb)["pid"], "r") as f:
            return int(f.read().strip())
    except (OSError, ValueError):
        return None


def cmd_run(kb: str, port: int):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    kb_root = os.path.realpath(kb)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=kb, **kw)

        def do_POST(self):
            """Local endpoints (bound to 127.0.0.1 only):
            /__delete__  {path}         -> delete a knowledge page, rebuild index
            /__config__  {blocked_topics} -> merge into config.json (topic filters)
            """
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                body = {}

            if self.path == "/__config__":
                try:
                    topics = body.get("blocked_topics", [])
                    if not isinstance(topics, list):
                        raise ValueError("blocked_topics must be a list")
                    topics = [str(t).strip() for t in topics if str(t).strip()]
                    cfg = load_config(kb_root)
                    cfg["blocked_topics"] = topics
                    save_config(kb_root, cfg)
                    payload, status = b'{"ok": true}', 200
                except Exception as e:
                    payload = json.dumps({"ok": False, "error": str(e)}).encode()
                    status = 400
            elif self.path == "/__delete__":
                try:
                    rel = str(body.get("path", "")).replace("\\", "/").lstrip("/")
                    target = os.path.realpath(os.path.join(kb_root, rel))
                    ok = (rel.endswith(".html")
                          and rel != "index.html"
                          and not rel.startswith("assets/")
                          and ".." not in rel.split("/")
                          and os.path.commonpath([target, kb_root]) == kb_root
                          and os.path.isfile(target))
                    if not ok:
                        raise ValueError("invalid path")
                    os.remove(target)
                    subprocess.run([sys.executable,
                                    os.path.join(script_dir, "build_index.py"),
                                    "--kb", kb_root],
                                   capture_output=True, timeout=120)
                    payload, status = b'{"ok": true}', 200
                except Exception as e:
                    payload = json.dumps({"ok": False, "error": str(e)}).encode()
                    status = 400
            else:
                self.send_error(404)
                return
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    http.server.ThreadingHTTPServer.allow_reuse_address = True
    server = http.server.ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"[interview-me] serving {kb} at http://127.0.0.1:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


def cmd_start(kb: str, port: int):
    os.makedirs(kb, exist_ok=True)
    pid = read_pid(kb)
    if pid and pid_alive(pid):
        cfg = load_config(kb)
        print(f"[interview-me] already running: "
              f"http://127.0.0.1:{cfg.get('port', port)} (PID {pid})")
        return
    cfg = load_config(kb)
    cfg["port"] = port
    save_config(kb, cfg)

    log = open(paths(kb)["log"], "a", encoding="utf-8")
    kwargs = dict(stdout=log, stderr=log, stdin=subprocess.DEVNULL, close_fds=True)
    if os.name == "nt":
        kwargs["creationflags"] = (subprocess.DETACHED_PROCESS
                                   | subprocess.CREATE_NEW_PROCESS_GROUP
                                   | getattr(subprocess, "CREATE_NO_WINDOW", 0))
    else:
        kwargs["start_new_session"] = True
    proc = subprocess.Popen(
        [sys.executable, os.path.abspath(__file__), "run",
         "--kb", kb, "--port", str(port)],
        **kwargs)
    with open(paths(kb)["pid"], "w") as f:
        f.write(str(proc.pid))
    print(f"[interview-me] started: http://127.0.0.1:{port} (PID {proc.pid})")


def cmd_stop(kb: str, port: int = None):
    pid = read_pid(kb)
    if not pid or not pid_alive(pid):
        print("[interview-me] not running")
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(pid), "/F"], capture_output=True)
    else:
        os.kill(pid, signal.SIGTERM)
    try:
        os.remove(paths(kb)["pid"])
    except OSError:
        pass
    print(f"[interview-me] stopped (PID {pid})")


def cmd_status(kb: str, port: int = None):
    pid = read_pid(kb)
    cfg = load_config(kb)
    if pid and pid_alive(pid):
        print(f"[interview-me] running: "
              f"http://127.0.0.1:{cfg.get('port', DEFAULT_PORT)} (PID {pid})")
    else:
        print("[interview-me] not running")


def main():
    ap = argparse.ArgumentParser(description="InterviewMe local server")
    ap.add_argument("action", choices=["run", "start", "stop", "status"])
    ap.add_argument("--kb", default=kb_default())
    ap.add_argument("--port", type=int, default=None)
    args = ap.parse_args()
    kb = os.path.abspath(args.kb)
    port = args.port or load_config(kb).get("port", DEFAULT_PORT)

    {"run": cmd_run, "start": cmd_start, "stop": cmd_stop,
     "status": cmd_status}[args.action](kb, port)


if __name__ == "__main__":
    main()
