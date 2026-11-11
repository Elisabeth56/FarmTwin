# ADR-005: Python interpreter mismatch on host
Date: 2026-08-17
Status: Accepted
Context: `python3` on this Mac resolves to Python 3.14; pydantic-core 
wheels don't build against PyO3 0.22 on 3.14 yet.
Decision: Use `/usr/local/bin/python3.11` explicitly for the venv:
`python3.11 -m venv .venv` (not `python3 -m venv .venv`).
Consequences: setup.sh on Day 7 must detect and use 3.11 specifically. 
Judges' machines may also have this issue.
