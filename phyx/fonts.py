"""Official Phyrexian typefaces from fxbuson/PhyrexianDictionary.

Phyrexian Regular (Wizards of the Coast) is the card font: its *family*
name is ``Phyrexian``, full name ``Phyrexian Regular``.  Basilica (GuruJ,
CC-BY) is the companion face with native hexadecimal glyphs.

Assets are GPL-3.0 / CC-BY and are fetched, not vendored.  A downloaded
file is rejected unless it is a real OpenType/TrueType container, so a
GitHub HTML error page can never be served as a font.
"""

from __future__ import annotations

import os
import shutil
import sys
import urllib.request
from pathlib import Path

FONT_FAMILY = "Phyrexian"
FONT_FULL_NAME = "Phyrexian Regular"
FONT_FILE = "Phyrexian-Regular.ttf"
FONT_REMOTE = (
    "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/main/fonts/"
    + FONT_FILE
)
FONT_CDN = (
    "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@main/fonts/"
    + FONT_FILE
)

BASILICA_FAMILY = "Basilica"
BASILICA_FILE = "Basilica.otf"
BASILICA_REMOTE = (
    "https://raw.githubusercontent.com/fxbuson/PhyrexianDictionary/main/fonts/"
    + BASILICA_FILE
)
BASILICA_CDN = (
    "https://cdn.jsdelivr.net/gh/fxbuson/PhyrexianDictionary@main/fonts/"
    + BASILICA_FILE
)

_SFNT_MAGIC = (b"\x00\x01\x00\x00", b"OTTO", b"true", b"typ1")
_WOFF_MAGIC = (b"wOFF", b"wOF2")


def assets_dir() -> Path:
    env = os.environ.get("PHYX_ASSETS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parent.parent / "assets"


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


def ensure_font(dest: Path | None = None) -> Path:
    """Return a valid local Phyrexian Regular file, downloading if needed."""
    path = dest if dest is not None else local_font()
    if is_font_file(path):
        return path
    return _download([FONT_CDN, FONT_REMOTE], path)


def ensure_basilica(dest: Path | None = None) -> Path:
    path = dest if dest is not None else local_basilica()
    if is_font_file(path):
        return path
    return _download([BASILICA_CDN, BASILICA_REMOTE], path)


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
    shutil.copy2(src, dest)
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
