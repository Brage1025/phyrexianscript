const vscode = require("vscode");
const { spawn } = require("child_process");
const fs = require("fs");
const os = require("os");
const path = require("path");
const fonts = require("./fonts");
const { lspCandidates } = require("./launch");

const LAUNCH_HOLD_MS = 5000;
const LAUNCH_WARNING = "φyrx: language features need Python 3.11 or newer with phyx installed (python -m pip install phyx). If phyx is installed somewhere else, set phyx.pythonPath.";

let fontOfferAttempted = false;
let languageServerStarted = false;
let launchWarningShown = false;

async function installFonts(context) {
  const dir = fonts.userFontDir(process.platform, process.env, os.homedir());
  try {
    await vscode.window.withProgress({
      location: vscode.ProgressLocation.Notification,
      title: "φyrx: Installing fonts",
    }, async () => {
      for (let i = 0; i < fonts.FONTS.length; i += 1) {
        const font = fonts.FONTS[i];
        const buffer = await fonts.downloadVerified(font.urls, font.sha256);
        await fonts.installFont({
          buffer,
          fileName: font.fileName,
          valueName: font.valueName,
          dir,
          platform: process.platform,
        });
      }
    });
  } catch (err) {
    const message = err && err.message ? err.message : String(err);
    await vscode.window.showErrorMessage(message);
    return;
  }
  fontOfferAttempted = true;
  if (context.globalState.get("phyx.fontOfferShown") === undefined) {
    context.globalState.update("phyx.fontOfferShown", true);
  }
  const installed = "The fonts were installed for this user. Restart VS Code to use them.";
  const choice = await vscode.window.showInformationMessage(
    installed,
    "Turn on Phyrexian font",
    "Reveal folder",
  );
  if (choice === "Turn on Phyrexian font") {
    await enablePhyrexianFont();
  } else if (choice === "Reveal folder") {
    await vscode.env.openExternal(vscode.Uri.file(dir));
  }
}

function phyxDocumentIsOpen(opened) {
  if (opened && opened.languageId === "phyx") {
    return true;
  }
  const docs = vscode.workspace.textDocuments;
  for (let i = 0; i < docs.length; i += 1) {
    if (docs[i].languageId === "phyx") {
      return true;
    }
  }
  return false;
}

function offerFontInstall(context, opened) {
  if (fontOfferAttempted) {
    return;
  }
  if (context.globalState.get("phyx.fontOfferShown") !== undefined) {
    return;
  }
  if (vscode.workspace.getConfiguration("phyx").get("offerFontInstall", true) !== true) {
    return;
  }
  if (!phyxDocumentIsOpen(opened)) {
    return;
  }
  const dir = fonts.userFontDir(process.platform, process.env, os.homedir());
  if (fonts.isInstalled(dir, "Phyrexian-Regular.ttf")) {
    return;
  }
  fontOfferAttempted = true;
  const shown = vscode.window.showInformationMessage(
    "Install the Phyrexian font so φyrx code looks right?",
    "Install",
    "Not now",
  );
  context.globalState.update("phyx.fontOfferShown", true);
  Promise.resolve(shown).then((choice) => {
    if (choice === "Install") {
      return vscode.commands.executeCommand("phyx.installFonts");
    }
    return undefined;
  }).catch(() => {});
}

async function unsetLanguageFont(scoped, target) {
  try {
    await scoped.update("editor.fontFamily", undefined, target, true);
  } catch (_err) {
    /* that scope has no settings file */
  }
}

async function enablePhyrexianFont() {
  const scoped = vscode.workspace.getConfiguration(undefined, { languageId: "phyx" });
  const inspected = scoped.inspect("editor.fontFamily") || {};
  const languageValue = inspected.workspaceFolderLanguageValue
    || inspected.workspaceLanguageValue
    || inspected.globalLanguageValue;
  const enabled = typeof languageValue === "string" && /^\s*Phyrexian\b/.test(languageValue);
  if (enabled) {
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
  await enablePhyrexianFont();
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
    if (this.disposed) {
      return;
    }
    this.disposed = true;
    for (const pending of this.pending.values()) {
      pending.reject(new Error("lsp"));
    }
    this.pending.clear();
    try {
      this.notify("exit", {});
      this.child.kill();
    } catch (_err) {
      /* ignore */
    }
  }
}

function runCandidate(context, candidate, cwd) {
  return new Promise((resolve) => {
    let child;
    try {
      child = spawn(candidate.cmd, candidate.args, {
        cwd,
        windowsHide: true,
        shell: false,
        stdio: ["pipe", "pipe", "pipe"],
      });
    } catch (_err) {
      resolve(false);
      return;
    }
    let settled = false;
    let session;
    let timer;
    const fail = () => {
      if (settled) {
        return;
      }
      settled = true;
      clearTimeout(timer);
      if (session) {
        session.dispose();
      } else {
        child.on("error", () => {});
        try {
          child.kill();
        } catch (_err) {
          /* already gone */
        }
      }
      resolve(false);
    };
    if (child.stderr) {
      child.stderr.on("data", () => {});
    }
    if (child.stdin) {
      child.stdin.on("error", () => {});
    }
    if (child.stdout) {
      child.stdout.on("error", () => {});
    }
    child.on("error", fail);
    child.on("exit", fail);
    try {
      session = connectLanguageServer(context, child);
    } catch (_err) {
      fail();
      return;
    }
    timer = setTimeout(() => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(true);
    }, LAUNCH_HOLD_MS);
  });
}

function pythonPathSetting() {
  const value = vscode.workspace.getConfiguration("phyx").get("pythonPath");
  return typeof value === "string" ? value : "";
}

function launchWarning(configured) {
  if (configured) {
    return `φyrx: could not start the language server with phyx.pythonPath set to ${configured}. Language features need Python 3.11 or newer with phyx installed (python -m pip install phyx).`;
  }
  return LAUNCH_WARNING;
}

async function warnLanguageServer(configured) {
  if (launchWarningShown) {
    return;
  }
  launchWarningShown = true;
  const choice = await vscode.window.showWarningMessage(launchWarning(configured), "Open Settings");
  if (choice === "Open Settings") {
    await vscode.commands.executeCommand("workbench.action.openSettings", "phyx.pythonPath");
  }
}

function connectLanguageServer(context, child) {
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

  const subscriptions = [];
  const add = (subscription) => {
    subscriptions.push(subscription);
    context.subscriptions.push(subscription);
  };
  add(rpc);
  add(vscode.workspace.onDidOpenTextDocument((doc) => {
    if (doc.languageId === "phyx") {
      sync(doc);
    }
  }));
  add(vscode.workspace.onDidChangeTextDocument((ev) => {
    if (ev.document.languageId !== "phyx") {
      return;
    }
    rpc.notify("textDocument/didChange", {
      textDocument: { uri: ev.document.uri.toString(), version: ev.document.version },
      contentChanges: [{ text: ev.document.getText() }],
    });
  }));
  add(vscode.languages.registerCompletionItemProvider(selector, {
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
  }, "-"));
  add(vscode.languages.registerDefinitionProvider(selector, {
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
  }));
  add(vscode.languages.registerHoverProvider(selector, {
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
  }));

  for (const doc of vscode.workspace.textDocuments) {
    if (doc.languageId === "phyx") {
      sync(doc);
    }
  }
  return {
    dispose() {
      while (subscriptions.length) {
        const subscription = subscriptions.pop();
        try {
          subscription.dispose();
        } catch (_err) {
          /* ignore */
        }
      }
    },
  };
}

function startLanguageServer(context, folder) {
  if (languageServerStarted) {
    return;
  }
  languageServerStarted = true;
  const configured = pythonPathSetting();
  let candidates = [];
  try {
    candidates = lspCandidates({
      setting: configured,
      env: process.env,
      platform: process.platform,
      exists: (candidate) => fs.existsSync(candidate),
    });
  } catch (_err) {
    warnLanguageServer(configured);
    return;
  }
  const cwd = folder || path.dirname(__dirname);
  const launch = async () => {
    for (const candidate of candidates) {
      const started = await runCandidate(context, candidate, cwd);
      if (started) {
        return;
      }
    }
    warnLanguageServer(configured);
  };
  launch().catch(() => {
    warnLanguageServer(configured);
  });
}

function activate(context) {
  const folder = vscode.workspace.workspaceFolders && vscode.workspace.workspaceFolders[0]
    ? vscode.workspace.workspaceFolders[0].uri.fsPath
    : undefined;
  context.subscriptions.push(
    vscode.commands.registerCommand("phyx.installFonts", () => installFonts(context)),
    vscode.commands.registerCommand("phyx.toggleFont", () => toggleFont()),
    vscode.workspace.onDidOpenTextDocument((doc) => {
      if (doc.languageId === "phyx") {
        offerFontInstall(context, doc);
      }
    }),
  );
  offerFontInstall(context);
  if (vscode.workspace.isTrusted) {
    startLanguageServer(context, folder);
    return;
  }
  context.subscriptions.push(vscode.workspace.onDidGrantWorkspaceTrust(() => {
    startLanguageServer(context, folder);
  }));
}

function deactivate() {}

module.exports = { activate, deactivate };
