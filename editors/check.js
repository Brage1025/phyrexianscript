"use strict";

const { spawnSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const editors = __dirname;
const errors = [];

function fail(message) {
  errors.push(message);
}

function globToRegExp(glob) {
  let re = "";
  let i = 0;
  while (i < glob.length) {
    if (glob[i] === "*" && glob[i + 1] === "*") {
      if (glob[i + 2] === "/") {
        re += "(?:.*/)?";
        i += 3;
        continue;
      }
      re += ".*";
      i += 2;
      continue;
    }
    if (glob[i] === "*") {
      re += "[^/]*";
      i += 1;
      continue;
    }
    if (glob[i] === "?") {
      re += "[^/]";
      i += 1;
      continue;
    }
    if ("\\.+^$()[]{}|".includes(glob[i])) {
      re += "\\" + glob[i];
    } else {
      re += glob[i];
    }
    i += 1;
  }
  return new RegExp("^" + re + "$");
}

function compileIgnore(line) {
  let pattern = line.trim();
  let negate = false;
  if (pattern.startsWith("!")) {
    negate = true;
    pattern = pattern.slice(1).trim();
  }
  let dirOnly = false;
  if (pattern.endsWith("/")) {
    dirOnly = true;
    pattern = pattern.slice(0, -1);
  }
  if (pattern.startsWith("/")) {
    pattern = pattern.slice(1);
  } else if (!pattern.includes("/")) {
    pattern = "**/" + pattern;
  }
  return { negate, dirOnly, regex: globToRegExp(pattern) };
}

function isIgnored(text, rel) {
  const specs = text.split(/\r?\n/).map((line) => line.trim()).filter((line) => line && !line.startsWith("#")).map(compileIgnore);
  const parts = rel.split("/");
  const paths = [];
  for (let n = 1; n <= parts.length; n += 1) {
    paths.push({ p: parts.slice(0, n).join("/"), isDir: n < parts.length });
  }
  let ignored = false;
  for (const spec of specs) {
    for (const entry of paths) {
      if (spec.dirOnly && !entry.isDir) {
        continue;
      }
      if (spec.regex.test(entry.p)) {
        ignored = !spec.negate;
        break;
      }
    }
  }
  return ignored;
}

function declaredCommands() {
  const manifest = JSON.parse(fs.readFileSync(path.join(editors, "package.json"), "utf8"));
  const commands = manifest.contributes && manifest.contributes.commands;
  if (!Array.isArray(commands)) {
    return [];
  }
  return commands.map((entry) => entry && entry.command).filter((id) => typeof id === "string" && id);
}

function commandsAreRegistered() {
  const source = fs.readFileSync(path.join(editors, "extension.js"), "utf8");
  for (const id of declaredCommands()) {
    const escaped = id.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const registered = new RegExp(`registerCommand\\s*\\(\\s*["']${escaped}["']`).test(source);
    if (!registered) {
      fail(`command ${id} is declared in package.json but not registered in extension.js`);
    }
  }
}

function noFontFiles() {
  const fontExt = new Set([".ttf", ".otf", ".woff", ".woff2"]);
  const walk = (dir) => {
    for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) {
        walk(full);
      } else if (fontExt.has(path.extname(entry.name).toLowerCase())) {
        fail(`font file under editors/: ${path.relative(editors, full)}`);
      }
    }
  };
  walk(editors);
}

function ignoreExcludesAssets() {
  const ignorePath = path.join(editors, ".vscodeignore");
  if (!fs.existsSync(ignorePath)) {
    fail("editors/.vscodeignore does not exist");
    return;
  }
  const text = fs.readFileSync(ignorePath, "utf8");
  if (!isIgnored(text, "assets/fonts/Phyrexian-Regular.ttf")) {
    fail("editors/.vscodeignore does not exclude assets/");
  }
  if (!isIgnored(text, "check.js")) {
    fail("editors/.vscodeignore does not exclude check.js");
  }
}

function syntaxCheck() {
  const target = path.join(editors, "extension.js");
  const result = spawnSync(process.execPath, ["--check", target], { encoding: "utf8" });
  if (result.status !== 0) {
    const detail = (result.stderr || result.stdout || "node --check failed").trim();
    fail(detail);
  }
}

commandsAreRegistered();
noFontFiles();
ignoreExcludesAssets();
syntaxCheck();

if (errors.length) {
  for (const message of errors) {
    process.stderr.write(`${message}\n`);
  }
  process.exit(1);
}
process.stdout.write("editors/check.js: ok\n");
