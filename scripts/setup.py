#!/usr/bin/env python3
"""Bootstrap only from the standard library; no global package modifications."""
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".venv"

def main():
    if not (3, 11) <= sys.version_info[:2] <= (3, 12):
        raise SystemExit("Install Python 3.11 or 3.12 from python.org, then open run.command again.")
    python = ENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    requirements = ROOT / "requirements.lock"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = ENV / ".jrm-dependencies"
    if not python.exists():
        print("Creating an isolated environment…", flush=True)
        venv.create(ENV, with_pip=True)
    if not marker.exists() or marker.read_text() != fingerprint:
        print("Installing pinned dependencies. First setup requires Internet access…", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "--only-binary=:all:", "-r", str(requirements)], check=True, cwd=ROOT)
        marker.write_text(fingerprint)
    try:
        subprocess.run([str(python), "-m", "jrm", "--download-model"], check=True, cwd=ROOT)
    except subprocess.CalledProcessError:
        print("Face model retrieval failed. Demo still works. Check your Internet connection and retry setup for webcam/video analysis.", flush=True)
    if "--setup-only" not in sys.argv:
        return subprocess.call([str(python), "-m", "jrm"], cwd=ROOT)
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError) as exc:
        print("Setup failed:", exc, file=sys.stderr)
        print("See README troubleshooting. No global Python packages were changed.", file=sys.stderr)
        raise SystemExit(1)
