"""Shared knowledge-base path resolution for InterviewMe scripts.

Priority order:
  1. explicit --kb CLI argument (handled by callers, never reaches here)
  2. INTERVIEW_ME_KB environment variable
  3. pointer file ~/.interview-me-path (written by install.py)
  4. default ~/.interview-me
"""
import os

POINTER = os.path.join(os.path.expanduser("~"), ".interview-me-path")
DEFAULT_KB = os.path.join(os.path.expanduser("~"), ".interview-me")


def default_kb() -> str:
    kb = os.environ.get("INTERVIEW_ME_KB")
    if kb:
        return kb
    try:
        with open(POINTER, encoding="utf-8") as f:
            p = f.read().strip()
            if p:
                return p
    except OSError:
        pass
    return DEFAULT_KB


def write_pointer(kb: str):
    try:
        with open(POINTER, "w", encoding="utf-8") as f:
            f.write(kb)
    except OSError:
        pass


def remove_pointer():
    try:
        os.remove(POINTER)
    except OSError:
        pass
