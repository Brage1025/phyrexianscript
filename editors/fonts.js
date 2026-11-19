"use strict";

const crypto = require("crypto");
const fs = require("fs");
const https = require("https");
const path = require("path");
const { execFile: defaultExecFile } = require("child_process");

// Pinned on 2026-11-19. `git ls-remote https://github.com/fxbuson/PhyrexianDictionary.git refs/heads/main`
// resolved refs/heads/main to FONT_COMMIT. PHYREXIAN_SHA256 and BASILICA_SHA256 are the SHA-256
// hashes of the files at
// https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/<FONT_COMMIT>/fonts/<file>.
// The second URL is the jsDelivr mirror of that same commit. These constants do not follow the main branch.

const FONT_COMMIT = "f3ea2bd41c433976493862325d91435dc3522cc3";

const PHYREXIAN_SHA256 = "a62fa75fbdb9f70e4a7873696158c5cdf440d78d156fd5557457b9ab7dc66ed7";
const BASILICA_SHA256 = "849687c0173606acbd920d2fe24e2019cdcdd7dac83182c69383bba187f9bfe2";

const PHYREXIAN_URLS = [
  "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/" + FONT_COMMIT + "/fonts/Phyrexian-Regular.ttf",
  "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@" + FONT_COMMIT + "/fonts/Phyrexian-Regular.ttf",
];

const BASILICA_URLS = [
  "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/" + FONT_COMMIT + "/fonts/Basilica.otf",
  "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@" + FONT_COMMIT + "/fonts/Basilica.otf",
];

const FONTS = [
  {
    fileName: "Phyrexian-Regular.ttf",
    valueName: "Phyrexian (TrueType)",
    sha256: PHYREXIAN_SHA256,
    urls: PHYREXIAN_URLS,
  },
  {
    fileName: "Basilica.otf",
    valueName: "Basilica (TrueType)",
    sha256: BASILICA_SHA256,
    urls: BASILICA_URLS,
  },
];

const MAX_BYTES = 5 * 1024 * 1024;
const TIMEOUT_MS = 30000;
const MAX_REDIRECTS = 5;
const UPSTREAM_CHANGED = "The font file changed upstream. Update the extension.";

const MAGICS = [
  Buffer.from([0x00, 0x01, 0x00, 0x00]),
  Buffer.from("OTTO", "latin1"),
  Buffer.from("true", "latin1"),
  Buffer.from("typ1", "latin1"),
];

function userFontDir(platform, env, home) {
  const envMap = env || {};
  const sep = platform === "win32" ? path.win32 : path.posix;
  if (platform === "win32") {
    const base = envMap.LOCALAPPDATA || sep.join(home, "AppData", "Local");
    return sep.join(base, "Microsoft", "Windows", "Fonts");
  }
  if (platform === "darwin") {
    return sep.join(home, "Library", "Fonts");
  }
  const base = envMap.XDG_DATA_HOME || sep.join(home, ".local", "share");
  return sep.join(base, "fonts");
}

function looksLikeFont(buffer) {
  if (!buffer || buffer.length < 12) {
    return false;
  }
  let head;
  try {
    head = Buffer.from(buffer.subarray(0, 4));
  } catch (_err) {
    return false;
  }
  for (let i = 0; i < MAGICS.length; i += 1) {
    if (head.equals(MAGICS[i])) {
      return true;
    }
  }
  return false;
}

function fontName(urls) {
  if (!urls || !urls.length) {
    return "the font";
  }
  try {
    const parts = new URL(urls[0]).pathname.split("/");
    const last = parts[parts.length - 1];
    if (last) {
      return decodeURIComponent(last);
    }
  } catch (_err) {
    /* use the fallback name */
  }
  return "the font";
}

function headerValue(headers, name) {
  if (!headers) {
    return undefined;
  }
  const wanted = name.toLowerCase();
  const keys = Object.keys(headers);
  for (let i = 0; i < keys.length; i += 1) {
    if (keys[i].toLowerCase() === wanted) {
      const value = headers[keys[i]];
      return Array.isArray(value) ? value[0] : value;
    }
  }
  return undefined;
}

function httpsGet(urlString, options) {
  const timeoutMs = options.timeoutMs;
  const maxBytes = options.maxBytes;
  return new Promise((resolve, reject) => {
    let settled = false;
    let req;
    const fail = (err) => {
      if (settled) {
        return;
      }
      settled = true;
      if (req) {
        req.destroy();
      }
      reject(err);
    };
    const ok = (value) => {
      if (settled) {
        return;
      }
      settled = true;
      resolve(value);
    };
    let parsed;
    try {
      parsed = new URL(urlString);
    } catch (err) {
      fail(err);
      return;
    }
    if (parsed.protocol !== "https:") {
      fail(new Error("only HTTPS URLs are allowed"));
      return;
    }
    req = https.request(
      {
        method: "GET",
        hostname: parsed.hostname,
        port: parsed.port || 443,
        path: parsed.pathname + parsed.search,
        headers: { "User-Agent": "phyx-extension", Accept: "*/*" },
      },
      (res) => {
        const chunks = [];
        let received = 0;
        res.on("data", (chunk) => {
          if (settled) {
            return;
          }
          received += chunk.length;
          if (received > maxBytes) {
            res.destroy();
            fail(new Error("the file is larger than 5 MiB"));
            return;
          }
          chunks.push(chunk);
        });
        res.on("end", () => {
          ok({
            statusCode: res.statusCode,
            headers: res.headers,
            body: Buffer.concat(chunks),
          });
        });
        res.on("error", (err) => {
          fail(err);
        });
      },
    );
    req.setTimeout(timeoutMs, () => {
      fail(new Error("the download timed out"));
    });
    req.on("error", (err) => {
      fail(err);
    });
    req.end();
  });
}

function isRedirect(status) {
  return status === 301 || status === 302 || status === 303 || status === 307 || status === 308;
}

async function fetchFollowing(url, transport) {
  let current = url;
  let followed = 0;
  for (;;) {
    const response = await transport(current, { timeoutMs: TIMEOUT_MS, maxBytes: MAX_BYTES });
    const status = Number(response.statusCode || response.status || 0);
    if (isRedirect(status)) {
      if (followed >= MAX_REDIRECTS) {
        throw new Error("too many redirects");
      }
      const location = headerValue(response.headers, "location");
      if (!location) {
        throw new Error("the server sent a redirect without a location");
      }
      followed += 1;
      current = new URL(location, current).href;
      continue;
    }
    const body = Buffer.isBuffer(response.body) ? response.body : Buffer.alloc(0);
    if (body.length > MAX_BYTES) {
      throw new Error("the file is larger than 5 MiB");
    }
    if (status !== 200) {
      throw new Error("the server returned " + status);
    }
    return body;
  }
}

async function downloadVerified(urls, sha256, transport) {
  const name = fontName(urls);
  const request = transport || httpsGet;
  const wanted = String(sha256).toLowerCase();
  let sawHashMismatch = false;
  let lastError = null;
  for (let i = 0; urls && i < urls.length; i += 1) {
    const url = urls[i];
    try {
      if (!transport) {
        const parsed = new URL(url);
        if (parsed.protocol !== "https:") {
          throw new Error("only HTTPS URLs are allowed");
        }
      }
      const body = await fetchFollowing(url, request);
      if (!looksLikeFont(body)) {
        throw new Error("the server did not return a font file");
      }
      const got = crypto.createHash("sha256").update(body).digest("hex");
      if (got !== wanted) {
        sawHashMismatch = true;
        throw new Error(UPSTREAM_CHANGED);
      }
      return body;
    } catch (err) {
      if (err && err.message === UPSTREAM_CHANGED) {
        sawHashMismatch = true;
      }
      lastError = err;
    }
  }
  if (sawHashMismatch) {
    throw new Error(UPSTREAM_CHANGED);
  }
  const reason = lastError && lastError.message ? lastError.message : "the download failed";
  throw new Error("Could not download " + name + ": " + reason + ".");
}

function locked(err) {
  return err && (err.code === "EBUSY" || err.code === "EPERM" || err.code === "EACCES");
}

function restartMessage(fileName) {
  return "Could not replace " + fileName + " because the file is in use. Restart the editor and run the command again.";
}

function runCaptured(execFile, file, args) {
  return new Promise((resolve, reject) => {
    execFile(file, args, { windowsHide: true, shell: false }, (err) => {
      if (err) {
        reject(err);
        return;
      }
      resolve();
    });
  });
}

async function installFont(options) {
  const buffer = options.buffer;
  const fileName = options.fileName;
  const valueName = options.valueName;
  const dir = options.dir;
  const platform = options.platform;
  const execFile = options.execFile || defaultExecFile;
  const writeFile = options.writeFile || fs.writeFileSync;
  fs.mkdirSync(dir, { recursive: true });
  const dest = path.resolve(dir, fileName);
  let exists = false;
  try {
    exists = fs.existsSync(dest);
  } catch (_err) {
    exists = false;
  }
  let same = false;
  if (exists) {
    try {
      same = fs.readFileSync(dest).equals(buffer);
    } catch (err) {
      if (locked(err)) {
        throw new Error(restartMessage(fileName));
      }
      throw err;
    }
  }
  if (!same) {
    try {
      writeFile(dest, buffer);
    } catch (err) {
      if (locked(err) && exists) {
        throw new Error(restartMessage(fileName));
      }
      throw err;
    }
  }
  if (platform === "win32") {
    const args = [
      "add",
      "HKCU\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\Fonts",
      "/v",
      valueName,
      "/t",
      "REG_SZ",
      "/d",
      dest,
      "/f",
    ];
    try {
      await runCaptured(execFile, "reg.exe", args);
    } catch (_err) {
      throw new Error("Could not register " + fileName + " for this user.");
    }
    return;
  }
  if (platform === "linux") {
    try {
      await runCaptured(execFile, "fc-cache", ["-f", dir]);
    } catch (_err) {
      /* fc-cache is missing or failed; the font file is already in place */
    }
  }
}

function isInstalled(dir, fileName) {
  const full = path.join(dir, fileName);
  let fd;
  try {
    fd = fs.openSync(full, "r");
    const buf = Buffer.alloc(12);
    const n = fs.readSync(fd, buf, 0, 12, 0);
    return looksLikeFont(n === 12 ? buf : buf.subarray(0, n));
  } catch (_err) {
    return false;
  } finally {
    if (fd !== undefined) {
      try {
        fs.closeSync(fd);
      } catch (_err) {
        /* ignore */
      }
    }
  }
}

module.exports = {
  FONT_COMMIT,
  FONTS,
  userFontDir,
  looksLikeFont,
  downloadVerified,
  installFont,
  isInstalled,
};
