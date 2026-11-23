"""Official Phyrexian typefaces from fxbuson/PhyrexianDictionary.

Phyrexian Regular (Wizards of the Coast) is the card font: its *family*
name is ``Phyrexian``, full name ``Phyrexian Regular``.  Basilica (GuruJ,
CC-BY) is the companion face with native hexadecimal glyphs.

Phyrexian Regular is Wizards of the Coast's font, used under the Fan Content Policy, and Basilica is by GuruJ under CC-BY 4.0.
Both are fetched, not vendored.  A downloaded
font is rejected unless it is a real OpenType/TrueType container, so a
GitHub HTML error page can never be served as a font.  ``phyx fetch``
downloads the fonts and the dictionary from pinned commits and checks
each file's SHA-256.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import sys
import urllib.request
from collections.abc import Mapping
from pathlib import Path

FONT_FAMILY = "Phyrexian"
FONT_FULL_NAME = "Phyrexian Regular"
FONT_FILE = "Phyrexian-Regular.ttf"
BASILICA_FAMILY = "Basilica"
BASILICA_FILE = "Basilica.otf"

# FONT_COMMIT is PhyrexianDictionary refs/heads/main. DICT_COMMIT is refs/heads/gh-pages.
# editors/fonts.js pins this same font commit and the same two font hashes.
FONT_COMMIT = "f3ea2bd41c433976493862325d91435dc3522cc3"
DICT_COMMIT = "740dd3797cbed2fe04c6c9509a71654c925ce9ea"
PHYREXIAN_SHA256 = "a62fa75fbdb9f70e4a7873696158c5cdf440d78d156fd5557457b9ab7dc66ed7"
BASILICA_SHA256 = "849687c0173606acbd920d2fe24e2019cdcdd7dac83182c69383bba187f9bfe2"
DICT_SHA256 = "9cb6c9edddf610d280dc03070a172535cbfd28afd1e13eac3e1c9926afc506e3"

_MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
_UPSTREAM_CHANGED = "The file changed upstream. Update phyx."
_RAW_ROOT = "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/"
_CDN_ROOT = "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@"
_DICT_PATH = "_data/PhyrexianAPI.json"

FONT_REMOTE = _RAW_ROOT + FONT_COMMIT + "/fonts/" + FONT_FILE
FONT_CDN = _CDN_ROOT + FONT_COMMIT + "/fonts/" + FONT_FILE
BASILICA_REMOTE = _RAW_ROOT + FONT_COMMIT + "/fonts/" + BASILICA_FILE
BASILICA_CDN = _CDN_ROOT + FONT_COMMIT + "/fonts/" + BASILICA_FILE
DICT_REMOTE = _RAW_ROOT + DICT_COMMIT + "/" + _DICT_PATH
DICT_CDN = _CDN_ROOT + DICT_COMMIT + "/" + _DICT_PATH

_SFNT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1")
_WOFF_MAGIC = (b"wOFF", b"wOF2")


def user_data_dir(platform: str, env: Mapping[str, str], home: Path) -> Path:
    """Per-user folder for an installed phyx. Does not create it.

    ``platform`` is a ``sys.platform`` value. ``env`` and ``home`` are
    arguments so a test can pass fakes and leave the real machine alone.
    """
    if platform == "win32":
        local = env.get("LOCALAPPDATA") or ""
        base = Path(local) if local else home / "AppData" / "Local"
        return base / "phyx"
    if platform == "darwin":
        return home / "Library" / "Application Support" / "phyx"
    data_home = env.get("XDG_DATA_HOME") or ""
    base = Path(data_home) if data_home else home / ".local" / "share"
    return base / "phyx"


def assets_dir(
    *,
    env: Mapping[str, str] | None = None,
    package_root: Path | None = None,
    platform: str | None = None,
    home: Path | None = None,
) -> Path:
    """Directory for fetched fonts and the dictionary. Does not create it.

    ``PHYX_ASSETS`` wins. A source checkout (``pyproject.toml`` in the
    directory above the ``phyx`` package) keeps ``<checkout>/assets``.
    An installed package uses :func:`user_data_dir`.
    """
    env_map = os.environ if env is None else env
    override = env_map.get("PHYX_ASSETS")
    if override:
        return Path(override)
    root = Path(__file__).resolve().parent.parent if package_root is None else package_root
    if (root / "pyproject.toml").is_file():
        return root / "assets"
    plat = sys.platform if platform is None else platform
    home_dir = Path.home() if home is None else home
    return user_data_dir(plat, env_map, home_dir)


def fonts_dir() -> Path:
    return assets_dir() / "fonts"


def local_font() -> Path:
    return fonts_dir() / FONT_FILE


def local_basilica() -> Path:
    return fonts_dir() / BASILICA_FILE


def is_font_bytes(data: bytes) -> bool:
    """True if ``data`` looks like OpenType, TrueType, or WOFF — not HTML."""
    if len(data) < 12:
        return False
    head = data[:4]
    return head in _SFNT_MAGIC or head in _WOFF_MAGIC


def is_font_file(path: Path | None) -> bool:
    if path is None or not path.is_file():
        return False
    try:
        with path.open("rb") as fh:
            return is_font_bytes(fh.read(12))
    except OSError:
        return False


def legacy_font(
    name: str,
    *,
    env: Mapping[str, str] | None = None,
    package_root: Path | None = None,
    platform: str | None = None,
    home: Path | None = None,
) -> Path | None:
    """Valid font left beside an install, when the user folder has no fonts yet.

    Reading may use that file. This does not copy it and does not create the
    user folder. A checkout, and ``PHYX_ASSETS``, have no legacy file.
    """
    env_map = os.environ if env is None else env
    if env_map.get("PHYX_ASSETS"):
        return None
    root = Path(__file__).resolve().parent.parent if package_root is None else package_root
    if (root / "pyproject.toml").is_file():
        return None
    plat = sys.platform if platform is None else platform
    home_dir = Path.home() if home is None else home
    user_fonts = user_data_dir(plat, env_map, home_dir) / "fonts"
    if user_fonts.is_dir() and any(is_font_file(child) for child in user_fonts.iterdir()):
        return None
    old = root / "assets" / "fonts" / name
    return old if is_font_file(old) else None


def matches_pin(path: Path, sha256: str) -> bool:
    """True when ``path`` is a file and its SHA-256 is ``sha256``."""
    if not path.is_file():
        return False
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return False
    return digest == sha256.lower()


def _read_limited(url: str, max_bytes: int) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "phyx-font-fetch"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - pinned https URLs
        final = resp.geturl()
        if not str(final).startswith("https://"):
            raise OSError(f"{url} redirected away from https")
        data = resp.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise OSError(f"the file is larger than {max_bytes} bytes")
    return data


def _write_atomic(dest: Path, data: bytes) -> None:
    """Write ``data`` to ``dest`` via a temporary file in the same folder.

    The temporary file is opened normally, so its mode follows the umask.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(f".{dest.name}.{os.getpid()}.part")
    try:
        with tmp.open("wb") as handle:
            handle.write(data)
        os.replace(tmp, dest)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def _fetch_error(name: str, last: Exception | None, mismatch: bool) -> OSError:
    if mismatch:
        return OSError(f"could not fetch {name}: {_UPSTREAM_CHANGED}")
    detail = str(last) if last is not None and str(last) else "the download failed"
    return OSError(f"could not fetch {name}: {detail}")


def _download(
    urls: list[str],
    dest: Path,
    expected_sha256: str,
    max_bytes: int,
    *,
    require_font: bool = True,
) -> Path:
    """Download ``dest`` from the first URL whose bytes match ``expected_sha256``."""
    wanted = expected_sha256.lower()
    last_err: Exception | None = None
    mismatch = False
    for url in urls:
        try:
            data = _read_limited(url, max_bytes)
        except OSError as err:
            last_err = err
            continue
        if require_font and not is_font_bytes(data):
            last_err = OSError(f"{url} did not return a font file")
            continue
        if hashlib.sha256(data).hexdigest() != wanted:
            mismatch = True
            last_err = OSError(_UPSTREAM_CHANGED)
            continue
        try:
            _write_atomic(dest, data)
        except OSError as err:
            last_err = err
            continue
        return dest
    raise _fetch_error(dest.name, last_err, mismatch)


def ensure_pinned(dest: Path, urls: list[str], sha256: str, *, require_font: bool = True) -> Path:
    """Make ``dest`` match ``sha256``.

    A file that already has that hash is returned without using the network.
    Otherwise the bytes are downloaded, checked, and written atomically.
    """
    if matches_pin(dest, sha256):
        return dest
    return _download(urls, dest, sha256, _MAX_DOWNLOAD_BYTES, require_font=require_font)


def _usable_font(dest: Path | None, default: Path) -> Path | None:
    path = default if dest is None else dest
    if is_font_file(path):
        return path
    if dest is None:
        return legacy_font(path.name)
    return None


def ensure_font(dest: Path | None = None) -> Path:
    """Return a valid local Phyrexian Regular file, downloading if needed."""
    found = _usable_font(dest, local_font())
    if found is not None:
        return found
    target = local_font() if dest is None else dest
    return _download([FONT_CDN, FONT_REMOTE], target, PHYREXIAN_SHA256, _MAX_DOWNLOAD_BYTES)


def ensure_basilica(dest: Path | None = None) -> Path:
    found = _usable_font(dest, local_basilica())
    if found is not None:
        return found
    target = local_basilica() if dest is None else dest
    return _download([BASILICA_CDN, BASILICA_REMOTE], target, BASILICA_SHA256, _MAX_DOWNLOAD_BYTES)


def install_user_font(src: Path, family: str) -> Path | None:
    """Copy ``src`` into the current user's font directory (Windows)."""
    if sys.platform != "win32":
        return None
    if not is_font_file(src):
        return None
    dest_dir = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft" / "Windows" / "Fonts"
    if not dest_dir.parent.is_dir():
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / src.name
    if not (dest.is_file() and dest.read_bytes() == src.read_bytes()):
        try:
            shutil.copy2(src, dest)
        except OSError as err:
            print(f"warning: could not install {dest}: {err}", file=sys.stderr)
            return None
    try:
        import winreg

        key = winreg.CreateKey(
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Fonts",
        )
        with key:
            winreg.SetValueEx(key, f"{family} (TrueType)", 0, winreg.REG_SZ, str(dest))
    except OSError:
        pass
    return dest
