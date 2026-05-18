"""
workflow — One-command local demo checks and launcher.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from urllib import error, request

from src.config import API_URL, MODEL, PROJECT_ROOT


def _ok(message: str) -> None:
    print(f"[ok] {message}")


def _warn(message: str) -> None:
    print(f"[warn] {message}")


def check_dependencies() -> bool:
    """Check Python packages and external tools needed for the demo."""
    required_modules = ["dotenv", "gradio", "yt_dlp", "pytest"]
    missing = [module for module in required_modules if importlib.util.find_spec(module) is None]
    if missing:
        _warn(f"Missing Python packages: {', '.join(missing)}")
        print("Run: pip install -r requirements.txt")
        return False

    if shutil.which("ffmpeg") is None:
        _warn("ffmpeg is not installed or not on PATH. Audio downloads/mashups may fail.")
    else:
        _ok("ffmpeg found")

    _ok("Python dependencies found")
    return True


def check_dataset() -> bool:
    """Validate the local dataset can be loaded and has required fields."""
    path = PROJECT_ROOT / "data" / "dataset.json"
    try:
        songs = json.loads(path.read_text())
    except Exception as exc:
        _warn(f"Could not read dataset: {exc}")
        return False

    required = {"song", "event", "mood", "genre", "energy"}
    bad_rows = [
        index
        for index, song in enumerate(songs, start=1)
        if not required.issubset(song)
    ]
    if bad_rows:
        _warn(f"Dataset rows missing required fields: {bad_rows[:5]}")
        return False

    _ok(f"Dataset loaded with {len(songs)} songs")
    return True


def run_tests() -> bool:
    """Run the local test suite before launching the presentation UI."""
    command = [sys.executable, "-m", "pytest", "tests/", "-q"]
    result = subprocess.run(command, cwd=PROJECT_ROOT, text=True, capture_output=True)
    if result.returncode != 0:
        _warn("Tests failed. Fix them before presenting.")
        print(result.stdout)
        print(result.stderr)
        return False
    _ok("Tests passed")
    return True


def check_ollama() -> bool:
    """Check whether the configured Ollama endpoint responds."""
    try:
        health_url = API_URL.rsplit("/", 1)[0] + "/tags"
        with request.urlopen(health_url, timeout=3) as response:
            response.read()
    except error.URLError:
        _warn("Ollama is not reachable.")
        print(f"Run: ollama run {MODEL}")
        return False

    _ok(f"Ollama reachable for model setting '{MODEL}'")
    return True


def run_workflow(launch_ui: bool = True) -> int:
    """
    Run setup checks, tests, Ollama validation, and optionally launch Gradio.

    The UI still launches if Ollama is unavailable so the app can show dataset
    matches and friendly error states during a presentation.
    """
    print("ShaadiSetlist local demo workflow\n", flush=True)
    deps_ok = check_dependencies()
    dataset_ok = check_dataset()
    tests_ok = run_tests()
    check_ollama()

    if not (deps_ok and dataset_ok and tests_ok):
        return 1

    if launch_ui:
        from src.gradio_ui import main as gradio_main

        gradio_main()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_workflow())
