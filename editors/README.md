# Editor support for φyrx

<img src="phyx-original.png" width="96" height="96" alt="φyrx">

Grammars for `.phyx` (row layout) and `.vphyx` (vertical columns). They highlight mood markers, verbs, constants, notes (`^rukx`), strings, and hexadecimal numerals.

`editors/` **is** a Cursor / VS Code extension (`package.json`).

Install from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=brage1025.phyx) (VS Code) or [Open VSX](https://open-vsx.org/extension/brage1025/phyx) (Cursor’s in-editor marketplace). Both listings are `brage1025.phyx`.

## Cursor / Visual Studio Code

From this repository, without the Marketplace:

1. Cursor / VS Code → **Extensions** → `…` → **Install from Location…** (or **Install from VSIX…** after packaging).
2. Choose the `editors/` folder.

Or copy the folder into the editor’s extensions directory (restart the editor after):

```
# Cursor, Windows
xcopy /E /I editors %USERPROFILE%\.cursor\extensions\brage1025.phyx-1.6.4

# VS Code, Windows
xcopy /E /I editors %USERPROFILE%\.vscode\extensions\brage1025.phyx-1.6.4
```

```
# Cursor, macOS / Linux
cp -R editors ~/.cursor/extensions/brage1025.phyx-1.6.4

# VS Code, macOS / Linux
cp -R editors ~/.vscode/extensions/brage1025.phyx-1.6.4
```

A VSIX, if you have Node:

```
npx --yes @vscode/vsce package --no-dependencies
```

That writes `phyx-1.6.4.vsix` in `editors/`. Then **Install from VSIX…**.

Completions, jump to `ťe`, and hover need `phyx` (or `python -m phyx`) on PATH. The extension starts `python -m phyx lsp`.

`.phyx` and `.vphyx` are associated with language id `phyx` (scope `source.phyx`).

`python -m phyx words` is the same lexicon the grammar was built from. After a lexicon change, regenerate:

```
python editors/_gen.py
```

`_gen.py` rewrites the TextMate and Vim grammars. It does not touch `package.json`.

## Font

`.phyx` can be shown in the Phyrexian font. The font is fetched onto your machine with `phyx fetch`. It is not bundled, and this extension ships no font file.

**φyrx: Install fonts** runs `phyx fetch` in an integrated terminal. It uses the same Python command the extension already uses to start `python -m phyx lsp` (`PHYX_PYTHON` when that is set, otherwise `phyx`, then `python -m phyx`, then `py -3 -m phyx`). The fonts are saved in the `assets/fonts` folder. On Windows they are installed for this user and VS Code must be restarted. On macOS and Linux, install them in the operating system, then reload VS Code. **Reveal folder** opens that folder in the file manager.

**φyrx: Toggle Phyrexian font** switches the language-scoped setting `[phyx]` → `editor.fontFamily` between `Phyrexian` followed by your current font as a fallback, and unset. Nothing turns the font on until you run the command. The font is proportional, so it is opt-in.

Phyrexian Regular is from the PhyrexianDictionary project under GPL-3.0; Basilica is by GuruJ under CC-BY.

φyrx is unofficial Fan Content permitted under the Fan Content Policy. Not approved/endorsed by Wizards. Portions of the materials used are property of Wizards of the Coast. ©Wizards of the Coast LLC.

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
