# AGENTS.md

## Project

- φyrx (PhyrxScript / PhyrexianScript): a programming language written in Phyrexian. Python 3.11+ interpreter in phyx/, no runtime dependencies.
- Behaviour is defined by docs/spec.md (normative). Design constraints are in docs/rationale.md.

## Commands

- Python tests: python -m unittest discover -s tests
- φyrx tests: python -m phyx test
- Reference engine: set PHYX_TREEWALK=1 (the tree-walker). The compiled engine is the default.

## Hard rules

- Never invent syntax or keywords that are not in the Phyrexian Dictionary. No floats, classes, infix operators or decimal literals. If a task seems to need a new word or syntax, stop and ask me.
- The compiler (phyx/compiler.py) and the tree-walker (phyx/interpreter.py) must behave identically. A semantic change is made in both and covered by a test that runs both.
- A behaviour change updates docs/spec.md, docs/reference.md and CHANGELOG.md in the same branch.
- Every fault is a PhyrexianError with a hint. A raw Python exception (ZeroDivisionError, TypeError and so on) reaching the user is always a bug.

## Workflow

- Work on a branch named cursor/topic. Never commit to main. One topic per branch.
- Write the failing test first and show it failing, then fix.
- No drive-by refactors and no reformatting of lines you were not asked to change.
- Never weaken, delete or skip an existing test to make something pass. If a test looks wrong, stop and explain.
- Do not commit dist/, *.egg-info, *.vsix, __pycache__, examples/*.html or assets/.
- Do not bump the version unless asked.
- Never add Co-authored-by or any other attribution trailer to a commit message.
- Files are UTF-8 with LF line endings.
- Reports contain what Definition of done asks for. Do not add 'Community Wisdom' sections, summaries of community posts, or offers to write blog posts.

## Definition of done

- python -m unittest discover -s tests and python -m phyx test both pass. They should also pass with PHYX_TREEWALK=1 (known exception until fixed: the bench test).
- End every task with a report: files changed, commands run with their results, anything not done, decisions you need from me.
