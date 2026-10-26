const vscode = require("vscode");
const { spawn, spawnSync } = require("child_process");
const path = require("path");

function phyxCandidates(subcommand) {
  const extra = process.env.PHYX_PYTHON;
  const tries = [];
  if (extra) {
    tries.push({
      cmd: extra,
      args: extra.toLowerCase().includes("phyx") ? [subcommand] : ["-m", "phyx", subcommand],
    });
  }
  tries.push({ cmd: "phyx", args: [subcommand] });
  tries.push({ cmd: "python", args: ["-m", "phyx", subcommand] });
  tries.push({ cmd: "py", args: ["-3", "-m", "phyx", subcommand] });
  return tries;
}

function candidateRuns(candidate) {
  const args = candidate.args.slice(0, -1).concat(["--version"]);
  const result = spawnSync(candidate.cmd, args, {
    windowsHide: true,
    timeout: 20000,
    stdio: "ignore",
  });
  return result.status === 0;
}

function resolvePhyx(subcommand) {
  const tries = phyxCandidates(subcommand);
  for (const candidate of tries) {
    if (candidateRuns(candidate)) {
      return candidate;
    }
  }
  return tries[0];
}

function spawnLsp(folder) {
  const cwd = folder || path.dirname(__dirname);
  let last;
  for (const t of phyxCandidates("lsp")) {
    try {
      last = spawn(t.cmd, t.args, { cwd, stdio: ["pipe", "pipe", "pipe"] });
      if (last.pid) {
        return last;
      }
    } catch (_err) {
      last = undefined;
    }
  }
  return last;
}

function fontsDirFromOutput(text) {
  const match = text.match(/->\s*(.+)/);
  if (!match) {
    return undefined;
  }
  return path.dirname(match[1].trim());
}

function fontsDirFromPython(candidate, cwd) {
  if (process.env.PHYX_ASSETS) {
    return path.join(process.env.PHYX_ASSETS, "fonts");
  }
  const code = "from phyx.fonts import fonts_dir; print(fonts_dir())";
  const probes = [];
  if (candidate.args[0] === "-3") {
    probes.push({ cmd: candidate.cmd, args: ["-3", "-c", code] });
  } else if (candidate.args.includes("-m")) {
    probes.push({ cmd: candidate.cmd, args: ["-c", code] });
  }
  probes.push({ cmd: "python", args: ["-c", code] });
  probes.push({ cmd: "py", args: ["-3", "-c", code] });
  for (const probe of probes) {
    const result = spawnSync(probe.cmd, probe.args, {
      cwd,
      encoding: "utf8",
      windowsHide: true,
      timeout: 20000,
    });
    if (result.status === 0 && result.stdout && result.stdout.trim()) {
      return result.stdout.trim().split(/\r?\n/).pop();
    }
  }
  if (cwd) {
    return path.join(cwd, "assets", "fonts");
  }
  return undefined;
}

function fetchSuccessMessage() {
  if (process.platform === "win32") {
    return "The fonts were installed for this user and VS Code must be restarted.";
  }
  return "The fonts are saved in the assets/fonts folder and must be installed in the operating system, then VS Code reloaded.";
}

async function revealFonts(fontsDir) {
  const choice = await vscode.window.showInformationMessage(
    fetchSuccessMessage(),
    "Reveal folder",
  );
  if (choice === "Reveal folder" && fontsDir) {
    await vscode.env.openExternal(vscode.Uri.file(fontsDir));
  }
}

function installFonts(folder) {
  const cwd = folder || path.dirname(__dirname);
  const candidate = resolvePhyx("fetch");
  let fontsDir = fontsDirFromPython(candidate, cwd);
  const writeEmitter = new vscode.EventEmitter();
  let proc;
  let captured = "";
  let reported = false;
  const pty = {
    onDidWrite: writeEmitter.event,
    open() {
      writeEmitter.fire(`${candidate.cmd} ${candidate.args.join(" ")}\r\n`);
      proc = spawn(candidate.cmd, candidate.args, {
        cwd,
        windowsHide: true,
        stdio: ["pipe", "pipe", "pipe"],
      });
      const take = (chunk) => {
        const text = chunk.toString("utf8");
        captured += text;
        writeEmitter.fire(text.replace(/\r?\n/g, "\r\n"));
      };
      proc.stdout.on("data", take);
      proc.stderr.on("data", take);
      proc.on("error", (err) => {
        reported = true;
        writeEmitter.fire(`${err.message}\r\n`);
        vscode.window.showWarningMessage("φyrx: could not start `phyx fetch`. Install phyx and keep Python on PATH.");
      });
      proc.on("exit", (code) => {
        if (reported) {
          return;
        }
        const fromOutput = fontsDirFromOutput(captured);
        if (fromOutput) {
          fontsDir = fromOutput;
        }
        if (code === 0) {
          revealFonts(fontsDir);
        } else {
          vscode.window.showWarningMessage("φyrx: `phyx fetch` failed. See the terminal.");
        }
      });
    },
    close() {
      if (proc) {
        proc.kill();
      }
    },
    handleInput(data) {
      if (data === "\u0003" && proc) {
        proc.kill();
        return;
      }
      if (proc && proc.stdin && proc.stdin.writable) {
        proc.stdin.write(data);
      }
    },
  };
  const term = vscode.window.createTerminal({ name: "φyrx: Install fonts", pty });
  term.show();
}

async function unsetLanguageFont(scoped, target) {
  try {
    await scoped.update("editor.fontFamily", undefined, target, true);
  } catch (_err) {
    /* that scope has no settings file */
  }
}

async function toggleFont() {
  const scoped = vscode.workspace.getConfiguration(undefined, { languageId: "phyx" });
  const inspected = scoped.inspect("editor.fontFamily") || {};
  const languageValue = inspected.workspaceFolderLanguageValue
    || inspected.workspaceLanguageValue
    || inspected.globalLanguageValue;
  const enabled = typeof languageValue === "string" && /^\s*Phyrexian\b/.test(languageValue);
  if (enabled) {
    if (inspected.workspaceFolderLanguageValue !== undefined) {
      await unsetLanguageFont(scoped, vscode.ConfigurationTarget.WorkspaceFolder);
    }
    if (inspected.workspaceLanguageValue !== undefined) {
      await unsetLanguageFont(scoped, vscode.ConfigurationTarget.Workspace);
    }
    if (inspected.globalLanguageValue !== undefined) {
      await unsetLanguageFont(scoped, vscode.ConfigurationTarget.Global);
    }
    return;
  }
  const base = vscode.workspace.getConfiguration().inspect("editor.fontFamily") || {};
  let current = base.workspaceFolderValue || base.workspaceValue || base.globalValue || base.defaultValue || "";
  if (typeof current !== "string") {
    current = "";
  }
  const fallback = current.replace(/^\s*Phyrexian\s*,\s*/, "");
  const next = fallback ? `Phyrexian, ${fallback}` : "Phyrexian";
  await scoped.update("editor.fontFamily", next, vscode.ConfigurationTarget.Global, true);
}

class Rpc {
  constructor(child) {
    this.child = child;
    this.nextId = 1;
    this.pending = new Map();
    this.buf = Buffer.alloc(0);
    child.stdout.on("data", (chunk) => this._onData(chunk));
    child.stderr.on("data", () => {});
  }

  _onData(chunk) {
    this.buf = Buffer.concat([this.buf, chunk]);
    while (true) {
      const headerEnd = this.buf.indexOf("\r\n\r\n");
      if (headerEnd < 0) {
        return;
      }
      const header = this.buf.slice(0, headerEnd).toString("ascii");
      const match = /Content-Length:\s*(\d+)/i.exec(header);
      if (!match) {
        this.buf = this.buf.slice(headerEnd + 4);
        continue;
      }
      const length = Number(match[1]);
      const start = headerEnd + 4;
      if (this.buf.length < start + length) {
        return;
      }
      const body = this.buf.slice(start, start + length).toString("utf8");
      this.buf = this.buf.slice(start + length);
      let msg;
      try {
        msg = JSON.parse(body);
      } catch (_err) {
        continue;
      }
      const pending = this.pending.get(msg.id);
      if (pending) {
        this.pending.delete(msg.id);
        if (msg.error) {
          pending.reject(new Error(msg.error.message || "lsp"));
        } else {
          pending.resolve(msg.result);
        }
      }
    }
  }

  notify(method, params) {
    this._send({ jsonrpc: "2.0", method, params });
  }

  request(method, params) {
    const id = this.nextId++;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this._send({ jsonrpc: "2.0", id, method, params });
    });
  }

  _send(payload) {
    const raw = Buffer.from(JSON.stringify(payload), "utf8");
    const header = Buffer.from(`Content-Length: ${raw.length}\r\n\r\n`, "ascii");
    this.child.stdin.write(Buffer.concat([header, raw]));
  }

  dispose() {
    try {
      this.notify("exit", {});
      this.child.kill();
    } catch (_err) {
      /* ignore */
    }
  }
}

function activate(context) {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
    ? vscode.workspace.workspaceFolders[0].uri.fsPath
    : undefined;
  context.subscriptions.push(
    vscode.commands.registerCommand("phyx.installFonts", () => installFonts(folder)),
    vscode.commands.registerCommand("phyx.toggleFont", () => toggleFont()),
  );
  const child = spawnLsp(folder);
  if (!child) {
    vscode.window.showWarningMessage("φyrx: could not start `python -m phyx lsp`. Install phyx and keep Python on PATH.");
    return;
  }
  const rpc = new Rpc(child);
  rpc.request("initialize", { processId: process.pid, capabilities: {} }).then(() => {
    rpc.notify("initialized", {});
  }).catch(() => {});

  const selector = { language: "phyx" };

  function sync(doc) {
    rpc.notify("textDocument/didOpen", {
      textDocument: { uri: doc.uri.toString(), languageId: "phyx", version: doc.version, text: doc.getText() },
    });
  }

  context.subscriptions.push(
    rpc,
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (doc.languageId === "phyx") {
        sync(doc);
      }
    }),
    vscode.workspace.onDidChangeTextDocument((ev) => {
      if (ev.document.languageId !== "phyx") {
        return;
      }
      rpc.notify("textDocument/didChange", {
        textDocument: { uri: ev.document.uri.toString(), version: ev.document.version },
        contentChanges: [{ text: ev.document.getText() }],
      });
    }),
    vscode.languages.registerCompletionItemProvider(selector, {
      async provideCompletionItems(doc, pos) {
        sync(doc);
        const items = await rpc.request("textDocument/completion", {
          textDocument: { uri: doc.uri.toString() },
          position: { line: pos.line, character: pos.character },
        });
        if (!Array.isArray(items)) {
          return [];
        }
        return items.map((it) => {
          const c = new vscode.CompletionItem(it.label, it.kind || vscode.CompletionItemKind.Text);
          c.detail = it.detail;
          if (it.documentation) {
            c.documentation = it.documentation;
          }
          return c;
        });
      },
    }, "-"),
    vscode.languages.registerDefinitionProvider(selector, {
      async provideDefinition(doc, pos) {
        sync(doc);
        const loc = await rpc.request("textDocument/definition", {
          textDocument: { uri: doc.uri.toString() },
          position: { line: pos.line, character: pos.character },
        });
        if (!loc || !loc.uri) {
          return undefined;
        }
        const start = new vscode.Position(loc.range.start.line, loc.range.start.character);
        return new vscode.Location(vscode.Uri.parse(loc.uri), start);
      },
    }),
    vscode.languages.registerHoverProvider(selector, {
      async provideHover(doc, pos) {
        sync(doc);
        const hover = await rpc.request("textDocument/hover", {
          textDocument: { uri: doc.uri.toString() },
          position: { line: pos.line, character: pos.character },
        });
        if (!hover || !hover.contents) {
          return undefined;
        }
        const value = hover.contents.value || hover.contents;
        return new vscode.Hover(String(value));
      },
    }),
  );

  for (const doc of vscode.workspace.textDocuments) {
    if (doc.languageId === "phyx") {
      sync(doc);
    }
  }
}

function deactivate() {}

module.exports = { activate, deactivate };
