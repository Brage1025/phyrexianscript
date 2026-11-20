"use strict";

const path = require("path");

const DEFAULT_PATHEXT = ".COM;.EXE;.BAT;.CMD";

function pathApi(platform) {
  return platform === "win32" ? path.win32 : path.posix;
}

function pathSeparator(platform) {
  return platform === "win32" ? ";" : ":";
}

function pathValue(env, platform) {
  if (!env) {
    return "";
  }
  if (platform === "win32") {
    return env.Path || "";
  }
  return env.PATH || "";
}

function fileNames(name, env, platform) {
  if (platform !== "win32") {
    return [name];
  }
  const raw = (env && env.PATHEXT) || DEFAULT_PATHEXT;
  return raw.split(";").filter((ext) => ext).map((ext) => name + ext);
}

function findOnPath(name, env, platform, exists) {
  const api = pathApi(platform);
  const dirs = pathValue(env, platform).split(pathSeparator(platform));
  const names = fileNames(name, env, platform);
  for (const dir of dirs) {
    if (!dir || dir === "." || dir === ".." || !api.isAbsolute(dir)) {
      continue;
    }
    for (const fileName of names) {
      const candidate = api.join(dir, fileName);
      if (exists(candidate)) {
        return candidate;
      }
    }
  }
  return undefined;
}

function looksLikePhyx(command) {
  return String(command).toLowerCase().includes("phyx");
}

function argsForCommand(command) {
  if (looksLikePhyx(command)) {
    return ["lsp"];
  }
  // -P (Python 3.11+) keeps the working directory off sys.path.
  return ["-P", "-m", "phyx", "lsp"];
}

function labelled(cmd, args, label) {
  return { cmd, args, label };
}

function resolveCommand(command, env, platform, exists) {
  const api = pathApi(platform);
  if (api.isAbsolute(command)) {
    return command;
  }
  if (!command || command === "." || command === ".." || command.includes("/") || command.includes("\\")) {
    return undefined;
  }
  return findOnPath(command, env, platform, exists);
}

function pushOnPath(list, name, args, env, platform, exists) {
  const cmd = findOnPath(name, env, platform, exists);
  if (!cmd) {
    return;
  }
  list.push(labelled(cmd, args.slice(), [name].concat(args).join(" ")));
}

function lspCandidates({ setting, env, platform, exists }) {
  const configured = typeof setting === "string" ? setting : "";
  if (configured !== "") {
    const args = argsForCommand(configured);
    return [labelled(configured, args, configured)];
  }
  const environment = env || {};
  const list = [];
  const chosen = environment.PHYX_PYTHON;
  if (chosen) {
    const cmd = resolveCommand(chosen, environment, platform, exists);
    if (cmd) {
      const args = argsForCommand(chosen);
      list.push(labelled(cmd, args, [chosen].concat(args).join(" ")));
    }
  }
  pushOnPath(list, "phyx", ["lsp"], environment, platform, exists);
  const pythonArgs = ["-P", "-m", "phyx", "lsp"];
  pushOnPath(list, "python", pythonArgs, environment, platform, exists);
  pushOnPath(list, "python3", pythonArgs, environment, platform, exists);
  if (platform === "win32") {
    pushOnPath(list, "py", ["-3", "-P", "-m", "phyx", "lsp"], environment, platform, exists);
  }
  return list;
}

module.exports = { findOnPath, lspCandidates };
