import json
import threading
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
from fbtranscript.android import Handler, _payload

def test_android_payload_defaults_to_audio_transcription():
    payload = _payload({})
    assert payload["whisper"] is True
    assert payload["model_size"] == "tiny"
    assert payload["languages"] == ["ar", "en", "all"]
    assert payload["translate_to"] is None

def test_android_payload_accepts_english_translation():
    payload = _payload({"translate_to": "en"})
    assert payload["translate_to"] == "en"

def test_android_payload_rejects_invalid_types():
    try:
        _payload({"whisper": "yes"})
    except ValueError as exc:
        assert "whisper" in str(exc)
    else:
        raise AssertionError("Invalid whisper value was accepted")

def test_android_http_health_and_web_assets():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with urlopen(base + "/api/v1/health") as response:
            health = json.loads(response.read())
            assert response.status == 200 and health["status"] == "ok"
        with urlopen(base + "/") as response:
            assert response.status == 200 and b"FBTranscript" in response.read()
        with urlopen(base + "/static/script.js") as response:
            script = response.read()
            assert b"waitForJob" in script and b"whisper:true" in script
            assert b"translate_to" in script
            assert b'querySelector("#whisper")' not in script
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
