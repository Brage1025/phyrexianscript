const vscode = require("vscode");
const { spawn } = require("child_process");
const path = require("path");

function spawnLsp(folder) {
  const extra = process.env.PHYX_PYTHON;
  const tries = [];
  if (extra) {
    tries.push({ cmd: extra, args: extra.toLowerCase().includes("phyx") ? ["lsp"] : ["-m", "phyx", "lsp"] });
  }
  tries.push({ cmd: "phyx", args: ["lsp"] });
  tries.push({ cmd: "python", args: ["-m", "phyx", "lsp"] });
  tries.push({ cmd: "py", args: ["-3", "-m", "phyx", "lsp"] });
  const cwd = folder || path.dirname(__dirname);
  let last;
  for (const t of tries) {
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
