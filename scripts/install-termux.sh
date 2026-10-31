#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail

REPO="https://github.com/galaxyuniversity900-oss/Facebook-Transcript-API-FBTranscript.git"
APP_DIR="${FBTRANSCRIPT_DIR:-$HOME/FBTranscript}"

echo "[1/5] Updating Termux packages..."
pkg update -y
pkg install -y python git ffmpeg

echo "[2/5] Getting FBTranscript..."
if [ -d "$APP_DIR/.git" ]; then
  git -C "$APP_DIR" pull --ff-only
else
  git clone "$REPO" "$APP_DIR"
fi

echo "[3/5] Installing the lightweight Android runtime..."
python -m pip install --upgrade pip
python -m pip install --no-cache-dir -e "$APP_DIR"

echo "[4/5] Creating launcher..."
mkdir -p "$HOME/bin"
cat > "$HOME/bin/fbtranscript" <<'LAUNCHER'
#!/data/data/com.termux/files/usr/bin/bash
set -Eeuo pipefail
cd "${FBTRANSCRIPT_DIR:-$HOME/FBTranscript}"
export PYTHONUNBUFFERED=1
exec python -m fbtranscript.android
LAUNCHER
chmod +x "$HOME/bin/fbtranscript"

echo "[5/5] Installation complete."
echo "Start with: ~/bin/fbtranscript"
echo "Open in your Android browser: http://127.0.0.1:8787"
