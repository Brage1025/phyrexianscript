"use strict";

const { describe, it } = require("node:test");
const assert = require("node:assert/strict");
const { findOnPath, lspCandidates } = require("./launch");

function recording(hits) {
  const have = new Set(hits || []);
  const checked = [];
  const exists = (candidate) => {
    checked.push(candidate);
    return have.has(candidate);
  };
  return { checked, exists };
}

describe("findOnPath", () => {
  it("ignores empty, relative, and dot entries and does not search the current directory", () => {
    const cwd = process.cwd();
    const checked = [];
    const exists = (candidate) => {
      checked.push(candidate);
      return candidate === cwd || candidate === "python" || candidate === "./python" || candidate.startsWith(cwd);
    };
    const found = findOnPath("python", {
      PATH: [".", "", "./bin", "rel/bin", "../bin", ".\\tools"].join(":"),
    }, "linux", exists);
    assert.ok(cwd);
    assert.equal(found, undefined);
    assert.deepEqual(checked, []);
  });

  it("respects PATH order and skips dot between absolute directories", () => {
    const { checked, exists } = recording(["/opt/bin/phyx"]);
    const found = findOnPath("phyx", { PATH: "/usr/bin:.:/opt/bin:/usr/bin" }, "linux", exists);
    assert.equal(found, "/opt/bin/phyx");
    assert.deepEqual(checked, ["/usr/bin/phyx", "/opt/bin/phyx"]);
  });

  it("returns the earlier absolute directory when both contain the name", () => {
    const exists = (candidate) => candidate === "/usr/bin/python" || candidate === "/opt/bin/python";
    assert.equal(
      findOnPath("python", { PATH: "/usr/bin:/opt/bin" }, "linux", exists),
      "/usr/bin/python",
    );
  });

  it("reads Path on win32 and tries PATHEXT in order", () => {
    const { checked, exists } = recording(["C:\\Py\\python.BAT"]);
    const found = findOnPath("python", {
      PATH: "C:\\Ignored",
      Path: ".;rel\\bin;C:\\Empty;C:\\Py",
      PATHEXT: ".COM;.EXE;.BAT;.CMD",
    }, "win32", exists);
    assert.equal(found, "C:\\Py\\python.BAT");
    assert.deepEqual(checked, [
      "C:\\Empty\\python.COM",
      "C:\\Empty\\python.EXE",
      "C:\\Empty\\python.BAT",
      "C:\\Empty\\python.CMD",
      "C:\\Py\\python.COM",
      "C:\\Py\\python.EXE",
      "C:\\Py\\python.BAT",
    ]);
  });

  it("uses the default PATHEXT when it is unset", () => {
    const { checked, exists } = recording([]);
    const found = findOnPath("phyx", { Path: "C:\\Tools" }, "win32", exists);
    assert.equal(found, undefined);
    assert.deepEqual(checked, [
      "C:\\Tools\\phyx.COM",
      "C:\\Tools\\phyx.EXE",
      "C:\\Tools\\phyx.BAT",
      "C:\\Tools\\phyx.CMD",
    ]);
  });
});

describe("lspCandidates", () => {
  const linuxFiles = [
    "/opt/bin/phyx",
    "/usr/bin/python",
    "/usr/bin/python3",
    "/usr/bin/py",
  ];

  function linux(setting, extra) {
    return lspCandidates({
      setting,
      env: Object.assign({ PATH: "/opt/bin:/usr/bin" }, extra || {}),
      platform: "linux",
      exists: (candidate) => linuxFiles.includes(candidate),
    });
  }

  it("orders PHYX_PYTHON, phyx, python, and python3 when the setting is empty", () => {
    const list = linux("", { PHYX_PYTHON: "/opt/custom/python" });
    assert.deepEqual(list.map((candidate) => candidate.cmd), [
      "/opt/custom/python",
      "/opt/bin/phyx",
      "/usr/bin/python",
      "/usr/bin/python3",
    ]);
    assert.deepEqual(list.map((candidate) => candidate.args), [
      ["-P", "-m", "phyx", "lsp"],
      ["lsp"],
      ["-P", "-m", "phyx", "lsp"],
      ["-P", "-m", "phyx", "lsp"],
    ]);
    assert.equal(list.some((candidate) => candidate.args[0] === "-3"), false);
  });

  it("orders phyx, python, and python3 without PHYX_PYTHON", () => {
    const list = linux("");
    assert.deepEqual(list.map((candidate) => candidate.label), [
      "phyx lsp",
      "python -P -m phyx lsp",
      "python3 -P -m phyx lsp",
    ]);
  });

  it("returns only the setting, with no fallback", () => {
    let called = false;
    const list = lspCandidates({
      setting: "D:\\Tools\\python.exe",
      env: { PATH: "/usr/bin", Path: "C:\\Windows", PHYX_PYTHON: "/usr/bin/phyx" },
      platform: "win32",
      exists: () => {
        called = true;
        return true;
      },
    });
    assert.equal(called, false);
    assert.deepEqual(list, [{
      cmd: "D:\\Tools\\python.exe",
      args: ["-P", "-m", "phyx", "lsp"],
      label: "D:\\Tools\\python.exe",
    }]);
  });

  it("runs a setting whose name contains phyx as phyx lsp", () => {
    const list = lspCandidates({
      setting: "C:\\Python\\Scripts\\phyx.exe",
      env: { Path: "C:\\Python", PHYX_PYTHON: "C:\\Python\\python.exe" },
      platform: "win32",
      exists: () => {
        throw new Error("setting does not search");
      },
    });
    assert.equal(list.length, 1);
    assert.equal(list[0].cmd, "C:\\Python\\Scripts\\phyx.exe");
    assert.deepEqual(list[0].args, ["lsp"]);
  });

  it("runs PHYX_PYTHON as phyx lsp when its name contains phyx", () => {
    const list = lspCandidates({
      setting: "",
      env: { PATH: "/usr/bin", PHYX_PYTHON: "/opt/bin/phyx" },
      platform: "linux",
      exists: () => false,
    });
    assert.deepEqual(list, [{
      cmd: "/opt/bin/phyx",
      args: ["lsp"],
      label: "/opt/bin/phyx lsp",
    }]);
  });

  it("runs PHYX_PYTHON as python -P -m phyx lsp when its name does not contain phyx", () => {
    const list = lspCandidates({
      setting: "",
      env: { PATH: "/usr/bin", PHYX_PYTHON: "/opt/python/bin/python3.11" },
      platform: "linux",
      exists: () => false,
    });
    assert.deepEqual(list, [{
      cmd: "/opt/python/bin/python3.11",
      args: ["-P", "-m", "phyx", "lsp"],
      label: "/opt/python/bin/python3.11 -P -m phyx lsp",
    }]);
  });

  it("resolves a bare PHYX_PYTHON name on PATH", () => {
    const list = linux("", { PHYX_PYTHON: "python3" });
    assert.equal(list[0].cmd, "/usr/bin/python3");
    assert.deepEqual(list[0].args, ["-P", "-m", "phyx", "lsp"]);
    const phyx = linux("", { PHYX_PYTHON: "phyx" });
    assert.equal(phyx[0].cmd, "/opt/bin/phyx");
    assert.deepEqual(phyx[0].args, ["lsp"]);
  });

  it("skips a relative PHYX_PYTHON instead of searching the current directory", () => {
    const checked = [];
    const list = lspCandidates({
      setting: "",
      env: { PATH: ".:./bin", PHYX_PYTHON: "./venv/bin/python" },
      platform: "linux",
      exists: (candidate) => {
        checked.push(candidate);
        return true;
      },
    });
    assert.deepEqual(list, []);
    assert.deepEqual(checked, []);
  });

  it("puts -P on every python invocation", () => {
    const list = linux("", { PHYX_PYTHON: "/opt/custom/python" });
    assert.ok(list.length >= 3);
    for (const candidate of list) {
      if (candidate.args.length === 1 && candidate.args[0] === "lsp") {
        continue;
      }
      assert.ok(candidate.args.includes("-P"), candidate.label);
      assert.equal(candidate.args[candidate.args[0] === "-3" ? 1 : 0], "-P");
    }
  });

  it("adds py -3 -P on win32 and keeps -P on python", () => {
    const list = lspCandidates({
      setting: "",
      env: { Path: "C:\\Tools", PATHEXT: ".EXE" },
      platform: "win32",
      exists: (candidate) => candidate.endsWith(".EXE"),
    });
    assert.deepEqual(list.map((candidate) => candidate.label), [
      "phyx lsp",
      "python -P -m phyx lsp",
      "python3 -P -m phyx lsp",
      "py -3 -P -m phyx lsp",
    ]);
    assert.deepEqual(list.map((candidate) => candidate.cmd), [
      "C:\\Tools\\phyx.EXE",
      "C:\\Tools\\python.EXE",
      "C:\\Tools\\python3.EXE",
      "C:\\Tools\\py.EXE",
    ]);
    assert.deepEqual(list[3].args, ["-3", "-P", "-m", "phyx", "lsp"]);
    for (const candidate of list) {
      if (candidate.args[0] === "lsp") {
        continue;
      }
      assert.ok(candidate.args.includes("-P"), candidate.label);
    }
  });
});
