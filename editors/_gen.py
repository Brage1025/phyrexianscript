"""One-shot: write TextMate + Vim grammars from phyx.vocabulary."""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from phyx.conjugation import CONJUGATIONS
from phyx.vocabulary import CONSTANTS, MARKERS, VERBS


def alt(words) -> str:
    return "|".join(sorted(words, key=lambda w: (-len(w), w)))


def vim_alt(words) -> str:
    return r"\%(" + r"\|".join(sorted(words, key=lambda w: (-len(w), w))) + r"\%)"


def main() -> None:
    verb_words = list(VERBS) + list(CONJUGATIONS)
    markers, verbs, constants = alt(MARKERS), alt(verb_words), alt(CONSTANTS)
    grammar = {
        "name": "φyrx",
        "scopeName": "source.phyx",
        "fileTypes": ["phyx", "vphyx"],
        "patterns": [
            {"include": "#shebang"},
            {"include": "#comment"},
            {"include": "#string"},
            {"include": "#number"},
            {"include": "#marker"},
            {"include": "#verb"},
            {"include": "#constant"},
            {"include": "#punctuation"},
        ],
        "repository": {
            "shebang": {
                "name": "comment.line.shebang.phyx",
                "match": "^#!.*$",
            },
            "comment": {
                "name": "comment.line.note.phyx",
                "match": r"\^rukx.*$",
            },
            "string": {
                "name": "string.quoted.double.phyx",
                "begin": '"',
                "end": '"',
                "patterns": [
                    {
                        "name": "constant.character.escape.phyx",
                        "match": r'\\[\\"nt]',
                    }
                ],
            },
            "number": {
                "name": "constant.numeric.hex.phyx",
                "match": r"əx?(?:[0-9A-Fa-f]|[\x{1D7F6}-\x{1D7FF}\x{1D670}-\x{1D675}\x{1D68A}-\x{1D68F}])+",
            },
            "marker": {
                "name": "keyword.control.marker.phyx",
                "match": rf"(?<![A-Za-z0-9_ə])(?:{markers})(?![A-Za-z0-9_])",
            },
            "verb": {
                "name": "keyword.operator.verb.phyx",
                "match": rf"(?<![A-Za-z0-9_ə])(?:{verbs})(?![A-Za-z0-9_])",
            },
            "constant": {
                "name": "constant.language.phyx",
                "match": rf"(?<![A-Za-z0-9_ə])(?:{constants})(?![A-Za-z0-9_])",
            },
            "punctuation": {
                "name": "punctuation.definition.sentence.phyx",
                "match": r"[\^!?.,:\-]",
            },
        },
    }
    (HERE / "phyx.tmLanguage.json").write_text(
        json.dumps(grammar, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    vim = f"""\" Vim syntax file
\" Language: φyrx (PhyrxScript / PhyrexianScript)
\" Filenames: *.phyx *.vphyx

if exists('b:current_syntax')
  finish
endif

syn match phyxShebang '^#!.*$'
syn match phyxComment '\\^rukx.*$'
syn region phyxString start='\"' skip='\\\\\\\\.' end='\"' contains=phyxEscape
syn match phyxEscape '\\\\\\\\[\\\\\"nt]' contained
syn match phyxNumber '\\<əx\\\\?[0-9][0-9a-fA-F]*\\>'
syn match phyxPunct '[\\^!?.,:\\-]'
syn match phyxMarker '{vim_alt(MARKERS)}'
syn match phyxVerb '{vim_alt(verb_words)}'
syn match phyxConstant '{vim_alt(CONSTANTS)}'

hi def link phyxShebang Comment
hi def link phyxComment Comment
hi def link phyxString String
hi def link phyxEscape SpecialChar
hi def link phyxNumber Number
hi def link phyxPunct Delimiter
hi def link phyxMarker Keyword
hi def link phyxVerb Operator
hi def link phyxConstant Constant

let b:current_syntax = 'phyx'
"""
    (HERE / "syntax").mkdir(exist_ok=True)
    (HERE / "syntax" / "phyx.vim").write_text(vim, encoding="utf-8")


if __name__ == "__main__":
    main()
