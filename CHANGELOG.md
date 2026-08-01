# Changelog

## 1.0.0 (2026-08-01)

First public release.

**Core**
- SessionEnd hook for automatic extraction + `/interview-me` manual mode
- JD / interview-prep mode: paste a JD or interview questions, get a researched prep roadmap
- General vs project knowledge; search-before-write dedup; one page per sub-domain
- Local website at 127.0.0.1:11123: study cards + collapsed interviewer Q&A

**Learning loop**
- Spaced repetition (1-3-7-14-30-60d), quiz mode with scope filter and keyboard control
- Learning dashboard: streak, activity heatmap, due counts
- Card delete with confirm, blocked-topics filter, light/dark theme

**Content**
- Offline LaTeX math (MathJax-SVG + full TeX extensions), code highlighting, markdown blocks
- Print-friendly pages, responsive tables, sticky TOC, in-page review button

**Ops**
- Idempotent installer; boot auto-start (--startup); KB pointer file; atomic index writes; no-cache server
