# Editor support for φyrx

Grammars for `.phyx` (row layout) and `.vphyx` (vertical columns). They highlight mood markers, verbs, constants, notes (`^rukx`), strings, and hexadecimal numerals.

`editors/` **is** a Cursor / VS Code extension (`package.json`).

Install from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=brage1025.phyx) (`brage1025.phyx`).

## Cursor / Visual Studio Code

From this repository, without the Marketplace:

1. Cursor / VS Code → **Extensions** → `…` → **Install from Location…** (or **Install from VSIX…** after packaging).
2. Choose the `editors/` folder.

Or copy the folder into the editor’s extensions directory (restart the editor after):

```
# Cursor, Windows
xcopy /E /I editors %USERPROFILE%\.cursor\extensions\brage1025.phyx-1.6.2

# VS Code, Windows
xcopy /E /I editors %USERPROFILE%\.vscode\extensions\brage1025.phyx-1.6.2
```

```
# Cursor, macOS / Linux
cp -R editors ~/.cursor/extensions/brage1025.phyx-1.6.2

# VS Code, macOS / Linux
cp -R editors ~/.vscode/extensions/brage1025.phyx-1.6.2
```

A VSIX, if you have Node:

```
npx --yes @vscode/vsce package --no-dependencies
```

That writes `phyx-1.6.2.vsix` in `editors/`. Then **Install from VSIX…**.

`.phyx` and `.vphyx` are associated with language id `phyx` (scope `source.phyx`).

`python -m phyx words` is the same lexicon the grammar was built from. After a lexicon change, regenerate:

```
python editors/_gen.py
```

`_gen.py` rewrites the TextMate and Vim grammars. It does not touch `package.json`.

## Vim / Neovim

```
set runtimepath+=/path/to/PhyrexianScript/editors
```

Or copy:

- `syntax/phyx.vim` → `~/.vim/syntax/phyx.vim`
- `ftdetect/phyx.vim` → `~/.vim/ftdetect/phyx.vim`

Neovim: the same paths under `~/.config/nvim/`.

## What is not highlighted on purpose

User ability names (`fib`, `sort`, `abs`) are not keywords. They are names you bind with `ťe`. The grammar only knows the dictionary.
