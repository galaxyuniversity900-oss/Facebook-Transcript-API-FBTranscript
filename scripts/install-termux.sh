#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO="https://github.com/galaxyuniversity900-oss/Facebook-Transcript-API-FBTranscript.git"
BRANCH="android/termux-native-runtime"
APP_DIR="${FBTRANSCRIPT_DIR:-$HOME/FBTranscript}"

echo "[1/5] Updating Termux packages..."
pkg update -y
pkg install -y python git

echo "[2/5] Getting the Android runtime branch..."
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" fetch origin "$BRANCH"
  git -C "$APP_DIR" checkout "$BRANCH"
  git -C "$APP_DIR" pull --ff-only origin "$BRANCH"
else
  git clone --branch "$BRANCH" --single-branch "$REPO" "$APP_DIR"
fi

echo "[3/5] Creating an isolated Python environment..."
python -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/python" -m pip install --upgrade pip
"$APP_DIR/.venv/bin/python" -m pip install --no-cache-dir --upgrade --force-reinstall "$APP_DIR"

echo "[4/5] Creating launcher..."
mkdir -p "$HOME/bin"
cat > "$HOME/bin/fbtranscript" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
cd "${FBTRANSCRIPT_DIR:-$HOME/FBTranscript}"
export PYTHONUNBUFFERED=1
exec "$PWD/.venv/bin/python" -m fbtranscript.android
LAUNCHER
chmod +x "$HOME/bin/fbtranscript"

echo "[5/5] Installation complete."
echo "Install the speech engine: bash scripts/install-whisper-termux.sh"
echo "Start with: ~/bin/fbtranscript"
echo "Open in browser: http://127.0.0.1:8787"
