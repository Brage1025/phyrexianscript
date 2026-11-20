"use strict";

const assert = require("node:assert/strict");
const crypto = require("node:crypto");
const fs = require("node:fs");
const http = require("node:http");
const os = require("node:os");
const path = require("node:path");
const { test } = require("node:test");

const fonts = require("./fonts");

const MAX_BYTES = 5 * 1024 * 1024;

function fontBytes(magic) {
  const buf = Buffer.alloc(16);
  const head = Buffer.isBuffer(magic) ? magic : Buffer.from(magic, "latin1");
  head.copy(buf);
  return buf;
}

function sha256(buffer) {
  return crypto.createHash("sha256").update(buffer).digest("hex");
}

function htmlPage() {
  return Buffer.from("<!DOCTYPE html><html><head><title>Not Found</title></head><body>404</body></html>");
}

function tempDir() {
  return fs.mkdtempSync(path.join(os.tmpdir(), "phyx-font-"));
}

function removeDir(dir) {
  fs.rmSync(dir, { recursive: true, force: true });
}

test("userFontDir uses the per-user font folder on each platform", () => {
  assert.equal(
    fonts.userFontDir("win32", { LOCALAPPDATA: "C:\\Users\\Me\\AppData\\Local" }, "C:\\Users\\Me"),
    "C:\\Users\\Me\\AppData\\Local\\Microsoft\\Windows\\Fonts",
  );
  assert.equal(
    fonts.userFontDir("darwin", {}, "/Users/me"),
    "/Users/me/Library/Fonts",
  );
  assert.equal(
    fonts.userFontDir("linux", {}, "/home/me"),
    "/home/me/.local/share/fonts",
  );
  assert.equal(
    fonts.userFontDir("linux", { XDG_DATA_HOME: "/xdg/data" }, "/home/me"),
    "/xdg/data/fonts",
  );
});

test("looksLikeFont accepts the four font magics and rejects HTML and short buffers", () => {
  assert.equal(fonts.looksLikeFont(fontBytes(Buffer.from([0x00, 0x01, 0x00, 0x00]))), true);
  assert.equal(fonts.looksLikeFont(fontBytes("OTTO")), true);
  assert.equal(fonts.looksLikeFont(fontBytes("true")), true);
  assert.equal(fonts.looksLikeFont(fontBytes("typ1")), true);
  assert.equal(fonts.looksLikeFont(htmlPage()), false);
  assert.equal(fonts.looksLikeFont(Buffer.alloc(0)), false);
  assert.equal(fonts.looksLikeFont(Buffer.from([0x00, 0x01, 0x00, 0x00])), false);
  assert.equal(fonts.looksLikeFont(Buffer.concat([Buffer.from([0x00, 0x01, 0x00, 0x00]), Buffer.alloc(7)])), false);
  assert.equal(fonts.looksLikeFont(fontBytes("wOFF")), false);
});

test("downloadVerified rejects an HTML page", async () => {
  const transport = async () => ({ statusCode: 200, headers: {}, body: htmlPage() });
  await assert.rejects(
    () => fonts.downloadVerified(["https://example.test/Phyrexian-Regular.ttf"], "ab".repeat(32), transport),
    (err) => err.message === "Could not download Phyrexian-Regular.ttf: the server did not return a font file.",
  );
});

test("downloadVerified rejects a hash mismatch", async () => {
  const body = fontBytes("OTTO");
  const transport = async () => ({ statusCode: 200, headers: {}, body });
  await assert.rejects(
    () => fonts.downloadVerified(["https://example.test/Phyrexian-Regular.ttf"], sha256(fontBytes("true")), transport),
    (err) => err.message === "The font file changed upstream. Update the extension.",
  );
});

test("downloadVerified falls back to the second URL when the first fails", async () => {
  const body = fontBytes("true");
  const calls = [];
  const transport = async (url, options) => {
    calls.push(url);
    assert.equal(options.timeoutMs, 30000);
    assert.equal(options.maxBytes, MAX_BYTES);
    if (calls.length === 1) {
      throw new Error("the connection was refused");
    }
    return { statusCode: 200, headers: {}, body };
  };
  const got = await fonts.downloadVerified(
    ["https://example.test/first", "https://cdn.example.test/Phyrexian-Regular.ttf"],
    sha256(body),
    transport,
  );
  assert.deepEqual(calls, [
    "https://example.test/first",
    "https://cdn.example.test/Phyrexian-Regular.ttf",
  ]);
  assert.ok(got.equals(body));
});

test("downloadVerified follows a redirect", async () => {
  const body = fontBytes("OTTO");
  const transport = async (url) => {
    if (url === "https://example.test/start") {
      return {
        statusCode: 302,
        headers: { Location: "https://example.test/Phyrexian-Regular.ttf" },
        body: Buffer.alloc(0),
      };
    }
    assert.equal(url, "https://example.test/Phyrexian-Regular.ttf");
    return { statusCode: 200, headers: {}, body };
  };
  const got = await fonts.downloadVerified(["https://example.test/start"], sha256(body), transport);
  assert.ok(got.equals(body));
});

test("downloadVerified allows five redirects and rejects a sixth", async () => {
  const body = fontBytes("typ1");
  const hash = sha256(body);
  const transport = async (url) => {
    const n = Number(url.slice(url.lastIndexOf("/") + 1));
    if (n < 5) {
      return {
        statusCode: 302,
        headers: { location: "https://example.test/" + (n + 1) },
        body: Buffer.alloc(0),
      };
    }
    return { statusCode: 200, headers: {}, body };
  };
  const got = await fonts.downloadVerified(["https://example.test/0"], hash, transport);
  assert.ok(got.equals(body));

  let calls = 0;
  const loop = async (url) => {
    calls += 1;
    return { statusCode: 302, headers: { location: url }, body: Buffer.alloc(0) };
  };
  await assert.rejects(
    () => fonts.downloadVerified(["https://example.test/Phyrexian-Regular.ttf"], hash, loop),
    (err) => err.message === "Could not download Phyrexian-Regular.ttf: too many redirects.",
  );
  assert.equal(calls, 6);
});

test("downloadVerified rejects a body above 5 MiB", async () => {
  const transport = async () => ({
    statusCode: 200,
    headers: {},
    body: Buffer.alloc(MAX_BYTES + 1),
  });
  await assert.rejects(
    () => fonts.downloadVerified(["https://example.test/Basilica.otf"], "ab".repeat(32), transport),
    (err) => err.message === "Could not download Basilica.otf: the file is larger than 5 MiB.",
  );
});

test("downloadVerified accepts a font of exactly 5 MiB", async () => {
  const body = Buffer.alloc(MAX_BYTES);
  Buffer.from("OTTO", "latin1").copy(body);
  const transport = async () => ({ statusCode: 200, headers: {}, body });
  const got = await fonts.downloadVerified(["https://example.test/Phyrexian-Regular.ttf"], sha256(body), transport);
  assert.equal(got.length, MAX_BYTES);
});

test("the default transport accepts HTTPS only", async () => {
  await assert.rejects(
    () => fonts.downloadVerified(["http://127.0.0.1/Phyrexian-Regular.ttf"], "ab".repeat(32)),
    (err) => err.message === "Could not download Phyrexian-Regular.ttf: only HTTPS URLs are allowed.",
  );
});

test("an injected transport can download from http://127.0.0.1", async () => {
  const body = fontBytes("OTTO");
  const server = http.createServer((req, res) => {
    res.writeHead(200, { "Content-Type": "application/octet-stream" });
    res.end(body);
  });
  await new Promise((resolve) => {
    server.listen(0, "127.0.0.1", resolve);
  });
  try {
    const port = server.address().port;
    const url = "http://127.0.0.1:" + port + "/Phyrexian-Regular.ttf";
    const transport = (target, options) => new Promise((resolve, reject) => {
      const req = http.get(target, (res) => {
        const chunks = [];
        res.on("data", (chunk) => chunks.push(chunk));
        res.on("end", () => {
          resolve({
            statusCode: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks),
          });
        });
      });
      req.setTimeout(options.timeoutMs, () => {
        req.destroy();
        reject(new Error("the download timed out"));
      });
      req.on("error", reject);
    });
    const got = await fonts.downloadVerified([url], sha256(body), transport);
    assert.ok(got.equals(body));
  } finally {
    await new Promise((resolve) => {
      server.close(resolve);
    });
  }
});

test("installFont writes a new file and skips an identical one", async () => {
  const dir = tempDir();
  try {
    const fileName = "Phyrexian-Regular.ttf";
    const buffer = fontBytes("OTTO");
    let writes = 0;
    await fonts.installFont({
      buffer,
      fileName,
      valueName: "Phyrexian (TrueType)",
      dir,
      platform: "darwin",
      writeFile(dest, data) {
        writes += 1;
        fs.writeFileSync(dest, data);
      },
      execFile() {
        throw new Error("darwin should not spawn");
      },
    });
    assert.equal(writes, 1);
    assert.ok(fs.readFileSync(path.join(dir, fileName)).equals(buffer));

    await fonts.installFont({
      buffer,
      fileName,
      valueName: "Phyrexian (TrueType)",
      dir,
      platform: "darwin",
      writeFile() {
        writes += 1;
        throw new Error("identical file should be skipped");
      },
    });
    assert.equal(writes, 1);

    const different = fontBytes("true");
    await fonts.installFont({
      buffer: different,
      fileName,
      valueName: "Phyrexian (TrueType)",
      dir,
      platform: "darwin",
    });
    assert.ok(fs.readFileSync(path.join(dir, fileName)).equals(different));
  } finally {
    removeDir(dir);
  }
});

test("installFont throws the restart message when a different file is locked", async () => {
  const dir = tempDir();
  try {
    const fileName = "Phyrexian-Regular.ttf";
    const existing = fontBytes("true");
    fs.writeFileSync(path.join(dir, fileName), existing);
    const codes = ["EBUSY", "EPERM", "EACCES"];
    for (let i = 0; i < codes.length; i += 1) {
      const code = codes[i];
      await assert.rejects(
        () => fonts.installFont({
          buffer: fontBytes("OTTO"),
          fileName,
          valueName: "Phyrexian (TrueType)",
          dir,
          platform: "darwin",
          writeFile() {
            const err = new Error("locked");
            err.code = code;
            throw err;
          },
        }),
        (err) => err.message === "Could not replace " + fileName + " because the file is in use. Restart the editor and run the command again.",
      );
      assert.ok(fs.readFileSync(path.join(dir, fileName)).equals(existing));
    }
  } finally {
    removeDir(dir);
  }
});

test("win32 registers the font with reg.exe and does not rewrite an identical file", async () => {
  const dir = tempDir();
  try {
    const cases = [
      ["Phyrexian-Regular.ttf", "Phyrexian (TrueType)"],
      ["Basilica.otf", "Basilica (TrueType)"],
    ];
    for (let i = 0; i < cases.length; i += 1) {
      const fileName = cases[i][0];
      const valueName = cases[i][1];
      const buffer = fontBytes(i === 0 ? "OTTO" : Buffer.from([0x00, 0x01, 0x00, 0x00]));
      fs.writeFileSync(path.join(dir, fileName), buffer);
      const calls = [];
      await fonts.installFont({
        buffer,
        fileName,
        valueName,
        dir,
        platform: "win32",
        writeFile() {
          throw new Error("identical file should be skipped");
        },
        execFile(cmd, args, options, cb) {
          calls.push({ cmd, args, shell: options.shell, windowsHide: options.windowsHide });
          cb(null);
        },
      });
      assert.equal(calls.length, 1);
      assert.equal(calls[0].cmd, "reg.exe");
      assert.equal(calls[0].shell, false);
      assert.equal(calls[0].windowsHide, true);
      assert.deepEqual(calls[0].args, [
        "add",
        "HKCU\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
        "/v",
        valueName,
        "/t",
        "REG_SZ",
        "/d",
        path.resolve(dir, fileName),
        "/f",
      ]);
    }
  } finally {
    removeDir(dir);
  }
});

test("linux runs fc-cache and ignores a missing binary", async () => {
  const dir = tempDir();
  try {
    const calls = [];
    await fonts.installFont({
      buffer: fontBytes("OTTO"),
      fileName: "Phyrexian-Regular.ttf",
      valueName: "Phyrexian (TrueType)",
      dir,
      platform: "linux",
      execFile(cmd, args, _options, cb) {
        calls.push({ cmd, args });
        const err = new Error("not found");
        err.code = "ENOENT";
        cb(err);
      },
    });
    assert.deepEqual(calls, [{ cmd: "fc-cache", args: ["-f", dir] }]);
    assert.equal(fonts.isInstalled(dir, "Phyrexian-Regular.ttf"), true);
  } finally {
    removeDir(dir);
  }
});

test("isInstalled requires a file that looks like a font", () => {
  const dir = tempDir();
  try {
    assert.equal(fonts.isInstalled(dir, "Phyrexian-Regular.ttf"), false);
    fs.writeFileSync(path.join(dir, "note.html"), htmlPage());
    assert.equal(fonts.isInstalled(dir, "note.html"), false);
    fs.writeFileSync(path.join(dir, "Phyrexian-Regular.ttf"), fontBytes("OTTO"));
    assert.equal(fonts.isInstalled(dir, "Phyrexian-Regular.ttf"), true);
  } finally {
    removeDir(dir);
  }
});

test("font URLs are pinned to a commit and not the main branch", () => {
  assert.match(fonts.FONT_COMMIT, /^[0-9a-f]{40}$/);
  assert.equal(fonts.FONTS.length, 2);
  assert.equal(fonts.FONTS[0].fileName, "Phyrexian-Regular.ttf");
  assert.equal(fonts.FONTS[0].valueName, "Phyrexian (TrueType)");
  assert.equal(fonts.FONTS[1].fileName, "Basilica.otf");
  assert.equal(fonts.FONTS[1].valueName, "Basilica (TrueType)");
  for (let i = 0; i < fonts.FONTS.length; i += 1) {
    const font = fonts.FONTS[i];
    assert.match(font.sha256, /^[0-9a-f]{64}$/);
    assert.equal(font.urls.length, 2);
    assert.match(font.urls[0], new RegExp("^https://raw\\.githubusercontent\\.com/fxbuson/PhyrexianDictionary/" + fonts.FONT_COMMIT + "/fonts/" + font.fileName + "$"));
    assert.match(font.urls[1], new RegExp("^https://cdn\\.jsdelivr\\.net/gh/fxbuson/PhyrexianDictionary@" + fonts.FONT_COMMIT + "/fonts/" + font.fileName + "$"));
    assert.equal(font.urls[0].includes("/main/"), false);
    assert.equal(font.urls[1].includes("@main"), false);
  }
});
