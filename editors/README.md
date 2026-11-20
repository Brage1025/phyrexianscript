# Editor support for φyrx

<img src="https://raw.githubusercontent.com/Brage1025/phyrexianscript/main/editors/phyx-original.png" width="96" height="96" alt="φyrx">

Grammars for `.phyx` (row layout) and `.vphyx` (vertical columns). They highlight mood markers, verbs, constants, notes (`^rukx`), strings, and hexadecimal numerals.

`editors/` **is** a Cursor / VS Code extension (`package.json`).

Install from the [Visual Studio Marketplace](https://marketplace.visualstudio.com/items?itemName=brage1025.phyx) (VS Code) or [Open VSX](https://open-vsx.org/extension/brage1025/phyx) (Cursor’s in-editor marketplace). Both listings are `brage1025.phyx`.

## Cursor / Visual Studio Code

From this repository, without the Marketplace:

1. In `editors/`, run `npx --yes @vscode/vsce package --no-dependencies`.
2. Extensions → `…` → **Install from VSIX…**.
3. Choose the `phyx-<version>.vsix` file written in `editors/`.

Or copy the folder into the editor’s extensions directory (restart the editor after):

```
# Cursor, Windows
xcopy /E /I editors %USERPROFILE%\.cursor\extensions\brage1025.phyx-1.7.0

# VS Code, Windows
xcopy /E /I editors %USERPROFILE%\.vscode\extensions\brage1025.phyx-1.7.0
```

```
# Cursor, macOS / Linux
cp -R editors ~/.cursor/extensions/brage1025.phyx-1.7.0

# VS Code, macOS / Linux
cp -R editors ~/.vscode/extensions/brage1025.phyx-1.7.0
```

A VSIX, if you have Node:

```
npx --yes @vscode/vsce package --no-dependencies
```

That writes `phyx-1.7.0.vsix` in `editors/`. Then **Install from VSIX…**.

`.phyx` and `.vphyx` are associated with language id `phyx` (scope `source.phyx`).

`python -m phyx words` is the same lexicon the grammar was built from. After a lexicon change, regenerate:

```
python editors/_gen.py
```

`_gen.py` rewrites the TextMate and Vim grammars. It does not touch `package.json`.

## Language server

Completions, jump to `ťe`, and hover come from the φyrx language server (`phyx lsp`). It needs Python 3.11 or newer with phyx installed (`python -m pip install phyx`).

`phyx.pythonPath` is the path to that Python interpreter or to a phyx executable. The setting is machine-scoped and defaults to empty. VS Code reads it from user settings, so a workspace `.vscode/settings.json` cannot choose the executable. An empty setting searches `PATH`. A filled-in setting is the only command the extension starts, so a wrong path fails on its own and the warning names that path.

Search order when the setting is empty: `PHYX_PYTHON`, then `phyx`, then `python`, then `python3`. On Windows, `py -3` comes last. A `PHYX_PYTHON` value or a `phyx.pythonPath` whose lowercase text contains `phyx` is run as `<path> lsp`. Any other interpreter is run as `<path> -P -m phyx lsp`. `python` and `python3` use `-P -m phyx lsp`. A `PATH` name is resolved to an absolute path from an absolute `PATH` directory. Empty entries, `.`, and relative entries are skipped, and the workspace folder is not a place the extension looks for the interpreter. `-P` (Python 3.11+) keeps that folder off `sys.path`, so a workspace that contains its own `phyx/` package cannot be the package Python imports. The server's working directory is still the workspace folder, because `bukð` looks up herds from the working directory.

In an untrusted workspace the language server stays off. Syntax highlighting and **φyrx: Install fonts** / **φyrx: Toggle Phyrexian font** still work. Trusting the workspace starts the server. If the server cannot start, one warning offers **Open Settings**, which opens `phyx.pythonPath`.

## Font

The extension installs Phyrexian Regular and Basilica itself. Python and `phyx` are not needed for the fonts. The files are downloaded from the PhyrexianDictionary project at a pinned commit, checked against a SHA-256 hash, and never bundled with the extension.

On Windows they are installed for the current user in `%LOCALAPPDATA%\Microsoft\Windows\Fonts`. Restart VS Code to use them. On macOS they go in `~/Library/Fonts`. On Linux they go in `$XDG_DATA_HOME/fonts`, or `~/.local/share/fonts` when `XDG_DATA_HOME` is unset. Restart VS Code to use them.

The first time a φyrx file is open, if Phyrexian Regular is not already installed, it asks "Install the Phyrexian font so φyrx code looks right?" That offer is shown once. Opening the command palette alone does not ask. Set `phyx.offerFontInstall` to false to switch it off.

**φyrx: Install fonts** downloads and installs both fonts. **Turn on Phyrexian font** turns the language font on when it is off, and **Reveal folder** opens the install folder in the file manager.

**φyrx: Toggle Phyrexian font** switches the language-scoped setting `[phyx]` → `editor.fontFamily` between `Phyrexian` followed by your current font as a fallback, and unset. Nothing turns the font on until you run that command or choose **Turn on Phyrexian font**. The font is proportional, so it is opt-in.

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
