#!/usr/bin/env bash
# Use CPython's signed universal2 distribution, on the ephemeral Intel CI runner.
set -euo pipefail
if [[ "${GITHUB_ACTIONS:-}" != "true" ]]; then
  echo "This installer is intended for GitHub-hosted CI only." >&2
  exit 1
fi
PACKAGE="$RUNNER_TEMP/python-3.14.10-macos11.pkg"
curl --fail --location --retry 3 --max-time 180 \
  https://www.python.org/ftp/python/3.14.10/python-3.14.10-macos11.pkg -o "$PACKAGE"
EXPECTED=286c7018aa2730f6747ca433dccdc2b31be45f078a9ea0ffa44d5f06368fd2d7
ACTUAL="$(shasum -a 256 "$PACKAGE" | cut -d ' ' -f1)"
[[ "$ACTUAL" == "$EXPECTED" ]] || { echo "CPython installer checksum mismatch" >&2; exit 1; }
sudo /usr/sbin/installer -pkg "$PACKAGE" -target /
/Library/Frameworks/Python.framework/Versions/3.14/bin/python3.14 -m venv .venv-universal
echo "$GITHUB_WORKSPACE/.venv-universal/bin" >> "$GITHUB_PATH"
lipo -archs /Library/Frameworks/Python.framework/Versions/3.14/Python
