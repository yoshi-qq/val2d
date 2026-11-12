"""Builds Val2d for Windows: dist/Val2d/Val2d.exe (game) and Val2d-Server.exe (dedicated server), zipped.

Usage:  python build.py                 checks dependencies, runs the tests, builds, self-tests the .exe, zips
        python build.py --skip-tests    same without pytest (the .exe self test still runs)

The build fails loudly if a dependency is missing, a test fails, or the built .exe cannot load every module,
config, map, sprite set and sound (play --self-test). Nothing is pushed or uploaded.
"""
from __future__ import annotations

import argparse
import importlib
import importlib.metadata as md
import os
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DIST = ROOT / "dist"
# PyInstaller's scratch folder lives outside the project: synced folders (OneDrive) lock files while it deletes them
WORK = Path(tempfile.gettempdir()) / "val2d-build"
NAME, SERVER = "Val2d", "Val2d-Server"

# (import name, distribution name, install hint). Keep in sync with requirements.txt.
REQUIRED = [
    ("pygame", "pygame-ce", "pip install pygame-ce"),
    ("networking", "networking", "pip install -r requirements.txt"),
    ("netplay", "netplay", "pip install -r requirements.txt"),
    ("PyInstaller", "pyinstaller", "pip install pyinstaller"),
    ("pytest", "pytest", "pip install pytest"),
]
# folders/files the game reads at runtime, relative to the project; copied next to the program
DATA = ["assets", "config", "font", "gameplay/data", "docs/design/character_sheet_spec.py"]
# modules loaded lazily (inside functions) or by path, so PyInstaller's import scan might miss them
HIDDEN = ["menu", "map_editor", "server", "user_settings", "self_test", "sprite_bank",
          "gameplay.abilities", "gameplay.bots", "gameplay.data", "gameplay.match", "gameplay.nav", "gameplay.net",
          "gameplay.netgame", "gameplay.session", "gameplay.world", "gameplay.geometry", "gameplay.hitzones",
          "gameplay.mapkit", "gameplay.kit", "gameplay.kit.dsl", "gameplay.kit.builtins", "gameplay.kit.presets"]  # config files import these
COLLECT = ["netplay", "networking", "gameplay", "client"]


def fail(message: str) -> None:
    print(f"\nBUILD FAILED: {message}")
    sys.exit(1)


def remove_tree(path: Path) -> None:
    """Delete a folder, retrying on files that a sync or virus scanner holds open for a moment."""
    def unlock(func, target, _info):  # type: ignore[no-untyped-def]
        os.chmod(target, stat.S_IWRITE)
        func(target)
    for attempt in range(6):
        if not path.exists():
            return
        try:
            shutil.rmtree(path, onerror=unlock)
            return
        except OSError:
            time.sleep(0.5 * (attempt + 1))
    if path.exists():
        fail(f"cannot delete {path} – close programs using it (Explorer window, running game) and pause OneDrive sync")


def check_dependencies() -> None:
    if sys.version_info < (3, 11):
        fail(f"Python 3.11+ needed, this is {sys.version.split()[0]}")
    missing = []
    for module, dist, hint in REQUIRED:
        try:
            importlib.import_module(module)
            print(f"  ok  {dist} {md.version(dist)}")
        except Exception as exc:  # report every missing piece at once
            missing.append(f"{dist} ({exc.__class__.__name__}) -> {hint}")
    try:
        md.version("pygame")
        missing.append("plain 'pygame' is installed next to pygame-ce; they clash -> pip uninstall pygame")
    except md.PackageNotFoundError:
        pass
    for item in DATA:
        if not (ROOT / item).exists():
            missing.append(f"data missing: {item}")
    if not list((ROOT / "assets" / "sounds").glob("*.wav")):
        missing.append("no sounds in assets/sounds -> python tools/make_sounds.py")
    if missing:
        fail("\n  " + "\n  ".join(missing))


def run_tests() -> None:
    print("\nRunning tests …")
    result = subprocess.run([sys.executable, "-m", "pytest", "-q", "tests"], cwd=ROOT)
    if result.returncode != 0:
        fail("tests failed")


def pyinstaller(script: str, name: str, windowed: bool) -> None:
    import PyInstaller.__main__
    args = [str(ROOT / script), "--name", name, "--noconfirm", "--clean", "--onedir",
            "--distpath", str(DIST), "--workpath", str(WORK), "--specpath", str(WORK),
            "--icon", str(ROOT / "assets" / "icon.ico"), "--paths", str(ROOT)]
    args.append("--windowed" if windowed else "--console")
    for item in DATA:
        src = ROOT / item
        dest = item if src.is_dir() else str(Path(item).parent)
        args += ["--add-data", f"{src}{os.pathsep}{dest}"]
    for module in HIDDEN:
        args += ["--hidden-import", module]
    for package in COLLECT:
        args += ["--collect-submodules", package]
    print(f"\nPyInstaller: {name} …")
    PyInstaller.__main__.run(args)


def self_test(exe: Path) -> None:
    report = WORK / f"{exe.stem}-self-test.txt"
    report.unlink(missing_ok=True)
    env = {**os.environ, "SDL_VIDEODRIVER": "dummy", "SDL_AUDIODRIVER": "dummy"}
    result = subprocess.run([str(exe), "--self-test", str(report)], env=env, timeout=180)
    text = report.read_text(encoding="utf-8") if report.exists() else "(no report written)"
    print(text)
    if result.returncode != 0 or "SELF-TEST OK" not in text:
        fail(f"{exe.name} failed its self test")


def main() -> None:
    ap = argparse.ArgumentParser(description="Build Val2d for Windows")
    ap.add_argument("--skip-tests", action="store_true")
    args = ap.parse_args()
    print("Checking dependencies …")
    check_dependencies()
    if not args.skip_tests:
        run_tests()
    remove_tree(DIST)
    remove_tree(WORK)
    pyinstaller("play.py", NAME, windowed=True)
    pyinstaller("server.py", SERVER, windowed=False)
    # one folder for players: the server exe and its own files go next to the game
    game_dir, server_dir = DIST / NAME, DIST / SERVER
    shutil.copy2(server_dir / f"{SERVER}.exe", game_dir / f"{SERVER}.exe")
    for item in (server_dir / "_internal").iterdir():
        target = game_dir / "_internal" / item.name
        if not target.exists():
            (shutil.copytree if item.is_dir() else shutil.copy2)(item, target)
    remove_tree(server_dir)
    print("\nSelf test of the built game …")
    self_test(game_dir / f"{NAME}.exe")
    version = subprocess.run(["git", "describe", "--always", "--dirty"], cwd=ROOT, capture_output=True, text=True).stdout.strip() or "local"
    archive = DIST / f"{NAME}-{version}-windows.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for path in game_dir.rglob("*"):
            z.write(path, Path(NAME) / path.relative_to(game_dir))
    size = archive.stat().st_size / 1e6
    print(f"\nBUILD OK: {game_dir / (NAME + '.exe')}\n          {archive} ({size:.0f} MB)")


if __name__ == "__main__":
    main()
