## Summary

## Checklist

- [ ] `python -m unittest discover -s tests -v`
- [ ] `python -m phyx test`
- [ ] `PHYX_TREEWALK=1 python -m unittest discover -s tests -v`
- [ ] `PHYX_TREEWALK=1 python -m phyx test`
- [ ] `ruff check .`
- [ ] A semantic change has a parity test in [`tests/test_engine_parity.py`](https://github.com/Brage1025/phyrexianscript/blob/main/tests/test_engine_parity.py). The compiled engine and the tree-walker agree.

On PowerShell, set `$env:PHYX_TREEWALK = "1"` for the two tree-walker commands. The forms are in CONTRIBUTING.md.
