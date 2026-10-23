#!/bin/bash
set -eu
cd -- "$(dirname -- "$0")"
PYTHON=""
for candidate in python3.12 python3.11 /opt/homebrew/bin/python3.12 /usr/local/bin/python3.12 python3; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c 'import sys; assert (3,11) <= sys.version_info[:2] <= (3,12)' >/dev/null 2>&1; then
    PYTHON="$candidate"
    break
  fi
done
if [ -z "$PYTHON" ]; then
  echo "Install Python 3.12 from https://www.python.org/downloads/macos/ then reopen run.command."
  read -r -p "Press Return to close. " _
  exit 1
fi
if ! "$PYTHON" scripts/setup.py; then
  echo "Launch failed. See the message above and README troubleshooting."
  read -r -p "Press Return to close. " _
  exit 1
fi
