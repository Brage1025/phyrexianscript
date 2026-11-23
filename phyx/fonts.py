"""Official Phyrexian typefaces from fxbuson/PhyrexianDictionary.

Phyrexian Regular (Wizards of the Coast) is the card font: its *family*
name is ``Phyrexian``, full name ``Phyrexian Regular``.  Basilica (GuruJ,
CC-BY) is the companion face with native hexadecimal glyphs.

Phyrexian Regular is Wizards of the Coast's font, used under the Fan Content Policy, and Basilica is by GuruJ under CC-BY 4.0.
Both are fetched, not vendored.  A downloaded
file is rejected unless it is a real OpenType/TrueType container, so a
GitHub HTML error page can never be served as a font.
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.request
from collections.abc import Mapping
from pathlib import Path

FONT_FAMILY = "Phyrexian"
FONT_FULL_NAME = "Phyrexian Regular"
FONT_FILE = "Phyrexian-Regular.ttf"
FONT_REMOTE = "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/main/fonts/" + FONT_FILE
FONT_CDN = "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@main/fonts/" + FONT_FILE

BASILICA_FAMILY = "Basilica"
BASILICA_FILE = "Basilica.otf"
BASILICA_REMOTE = "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/main/fonts/" + BASILICA_FILE
BASILICA_CDN = "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@main/fonts/" + BASILICA_FILE

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


def _download(urls: list[str], dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    last_err: Exception | None = None
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "phyx-font-fetch"})
            with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310
                data = resp.read()
        except OSError as err:
            last_err = err
            continue
        if not is_font_bytes(data):
            last_err = ValueError(f"{url} did not return a font file")
            continue
        dest.write_bytes(data)
        return dest
    raise OSError(f"could not fetch {dest.name}: {last_err}")


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
    return _download([FONT_CDN, FONT_REMOTE], dest if dest is not None else local_font())


def ensure_basilica(dest: Path | None = None) -> Path:
    found = _usable_font(dest, local_basilica())
    if found is not None:
        return found
    return _download([BASILICA_CDN, BASILICA_REMOTE], dest if dest is not None else local_basilica())


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
