#!/usr/bin/env python3
"""InterviewMe - rebuild the self-contained index.html and self-heal index.json.

Usage: python build_index.py [--kb KB_DIR]

Knowledge base layout:
  <kb>/index.html                            generated site (data inlined)
  <kb>/index.json                            machine index for dedup decisions
  <kb>/<Category>/[sub/]<sub-domain>.html    general knowledge pages
  <kb>/projects/<project>/<topic>.html       project knowledge pages
"""
import argparse
import datetime
import json
import os
import re
import shutil
import sys
from html import unescape
from html.parser import HTMLParser

from kbutil import default_kb as _default_kb

SKIP_DIRS = {".git", "__pycache__", "logs", "node_modules"}
RESERVED_DIRS = {"projects", "assets"}
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PORT = 11123


def kb_default() -> str:
    return _default_kb()


def extract_html_meta(html_path: str):
    """Fallback metadata: pull <h1> title and .overview summary from a page."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return None, ""
    m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.S)
    title = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else None
    m = re.search(r'class="overview"[^>]*>(.*?)</p>', text, re.S)
    summary = re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
    return title, summary


def walk_html(root: str):
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if not d.startswith(".") and d not in SKIP_DIRS]
        for fn in sorted(files):
            if fn.endswith(".html"):
                yield os.path.join(dirpath, fn)


class QAExtractor(HTMLParser):
    """Depth-aware extractor for top-level <details class="qa"> blocks.

    Regex cannot handle the nested <details class="follow"> inside answers,
    so we track the open-<details> depth. Question = first <summary> text,
    answer = the remaining inner HTML (follow-ups included). Entity refs are
    preserved raw so the answer can be re-injected via innerHTML safely.
    """

    MAX_ANSWER = 4000  # chars, guard against bloated payloads

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.qas = []
        self.qa_depth = 0        # open <details> depth inside current qa (0 = outside)
        self.in_summary = False
        self.summary_done = False
        self.cur_q = []
        self.cur_a = []

    def _sink(self):
        return self.cur_q if self.in_summary else self.cur_a

    def handle_starttag(self, tag, attrs):
        cls = dict(attrs).get("class", "")
        if tag == "details" and self.qa_depth == 0 and "qa" in cls.split():
            self.qa_depth = 1
            self.summary_done = False
            self.cur_q, self.cur_a = [], []
            return
        if self.qa_depth:
            if tag == "details":
                self.qa_depth += 1
            if tag == "summary" and self.qa_depth == 1 and not self.summary_done:
                self.in_summary = True
                return
            self._sink().append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        if self.qa_depth:
            self._sink().append(self.get_starttag_text())

    def handle_endtag(self, tag):
        if not self.qa_depth:
            return
        if tag == "summary" and self.in_summary:
            self.in_summary = False
            self.summary_done = True
            return
        if tag == "details":
            self.qa_depth -= 1
            if self.qa_depth == 0:
                q = "".join(self.cur_q).strip()
                a = "".join(self.cur_a).strip()[:self.MAX_ANSWER]
                if q:
                    self.qas.append({"q": q, "a": a})
            else:
                self.cur_a.append("</details>")
            return
        self._sink().append(f"</{tag}>")

    def handle_data(self, data):
        if self.qa_depth:
            self._sink().append(data)

    def handle_entityref(self, name):
        if self.qa_depth:
            self._sink().append(f"&{name};")

    def handle_charref(self, name):
        if self.qa_depth:
            self._sink().append(f"&#{name};")


def ensure_assets(kb: str):
    """Copy vendored JS/CSS assets into the KB so pages can render math,
    code highlighting and markdown offline. Self-healing: re-copied when
    missing or when the repo copy is newer."""
    src = os.path.join(SCRIPT_DIR, "..", "assets")
    dst = os.path.join(kb, "assets")
    if not os.path.isdir(src):
        return
    for root, dirs, files in os.walk(src):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        rel = os.path.relpath(root, src)
        for fn in files:
            s = os.path.join(root, fn)
            d = os.path.join(dst, rel, fn) if rel != "." else os.path.join(dst, fn)
            if (not os.path.exists(d)
                    or os.path.getmtime(s) > os.path.getmtime(d)):
                os.makedirs(os.path.dirname(d), exist_ok=True)
                shutil.copy2(s, d)


def extract_qas(html_path: str):
    """Pull the interview Q&A bank out of a knowledge page (for quiz mode)."""
    try:
        with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
    except OSError:
        return []
    parser = QAExtractor()
    try:
        parser.feed(text)
        parser.close()
    except Exception:
        pass
    return parser.qas


def scan_pages(kb: str) -> dict:
    """Return {rel_path: {"type": general|project, "group": name, "abs": path}}."""
    pages = {}
    for entry in sorted(os.listdir(kb)):
        d = os.path.join(kb, entry)
        if (not os.path.isdir(d) or entry.startswith(".")
                or entry in SKIP_DIRS or entry in RESERVED_DIRS):
            continue
        for p in walk_html(d):
            rel = os.path.relpath(p, kb).replace(os.sep, "/")
            pages[rel] = {"type": "general", "group": entry, "abs": p}
    projects_root = os.path.join(kb, "projects")
    if os.path.isdir(projects_root):
        for proj in sorted(os.listdir(projects_root)):
            d = os.path.join(projects_root, proj)
            if not os.path.isdir(d) or proj.startswith("."):
                continue
            for p in walk_html(d):
                rel = os.path.relpath(p, kb).replace(os.sep, "/")
                pages[rel] = {"type": "project", "group": proj, "abs": p}
    return pages


def atomic_write(path: str, content: str):
    """Write via temp file + rename so concurrent readers never see a
    truncated file (two extraction sessions may run at once)."""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(content)
    os.replace(tmp, path)


def build(kb: str) -> dict:
    kb = os.path.abspath(kb)
    os.makedirs(kb, exist_ok=True)
    ensure_assets(kb)
    json_path = os.path.join(kb, "index.json")

    old_entries = {}
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                for e in json.load(f).get("knowledge", []):
                    old_entries[e.get("path", "")] = e
        except (json.JSONDecodeError, OSError):
            pass

    today = datetime.date.today().isoformat()
    pages = scan_pages(kb)
    knowledge = []
    for rel, info in sorted(pages.items()):
        old = old_entries.get(rel, {})
        title = old.get("title")
        summary = old.get("summary", "")
        if not title:  # on disk but missing from index.json -> parse from HTML
            title, fallback_summary = extract_html_meta(info["abs"])
            summary = summary or fallback_summary
        if not title:
            title = os.path.splitext(os.path.basename(rel))[0]
        updated = old.get("updated") or datetime.date.fromtimestamp(
            os.path.getmtime(info["abs"])).isoformat()
        knowledge.append({
            # unescape defensively: some extractors write "&amp;" into
            # index.json, which would otherwise double-escape in the UI
            "title": unescape(title),
            "path": rel,
            "type": info["type"],
            "group": info["group"],
            "summary": unescape(summary),
            "related": old.get("related", []),
            "updated": updated,
        })

    atomic_write(json_path,
                 json.dumps({"knowledge": knowledge}, ensure_ascii=False, indent=2))

    warnings = []

    def group_of(kind):
        groups = {}
        for e in knowledge:
            if e["type"] != kind:
                continue
            qas = extract_qas(pages[e["path"]]["abs"])
            # quiz-bank health check: page declares a Q&A section but nothing
            # was extractable -> the page likely broke the template contract
            if not qas:
                try:
                    with open(pages[e["path"]]["abs"], "r",
                              encoding="utf-8", errors="ignore") as f:
                        body = f.read()
                    if 'class="qa"' in body or "Q&A" in body or "Q&amp;A" in body:
                        warnings.append(e["path"])
                except OSError:
                    pass
            groups.setdefault(e["group"], []).append({
                "title": e["title"], "path": e["path"],
                "summary": e["summary"], "updated": e["updated"],
                # quiz bank: extracted live from the page, kept out of index.json
                "qa": qas,
            })
        return [{"name": n, "pages": p} for n, p in sorted(groups.items())]

    port = DEFAULT_PORT
    blocked = []
    cfg_path = os.path.join(kb, "config.json")
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                port = cfg.get("port", DEFAULT_PORT)
                blocked = cfg.get("blocked_topics", [])
        except (json.JSONDecodeError, OSError):
            pass

    data = {
        "generated": today,
        "port": port,
        "blocked_topics": blocked,
        "categories": group_of("general"),
        "projects": group_of("project"),
    }

    template_path = os.path.join(SCRIPT_DIR, "..", "templates",
                                 "index.template.html")
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    html = template.replace("__DATA__", payload)
    out = os.path.join(kb, "index.html")
    atomic_write(out, html)

    for w in warnings:
        print(f"[interview-me] WARNING: {w} has a Q&A section but no "
              f"extractable <details class=\"qa\"> items; quiz bank skips it.")

    return {"pages": len(knowledge),
            "categories": len(data["categories"]),
            "projects": len(data["projects"]),
            "index": out}


def main():
    ap = argparse.ArgumentParser(description="InterviewMe index builder")
    ap.add_argument("--kb", default=kb_default(), help="knowledge base root")
    args = ap.parse_args()
    r = build(args.kb)
    print(f"[interview-me] index.html rebuilt: {r['index']} "
          f"({r['pages']} pages, {r['categories']} categories, "
          f"{r['projects']} projects)")


if __name__ == "__main__":
    sys.exit(main())
