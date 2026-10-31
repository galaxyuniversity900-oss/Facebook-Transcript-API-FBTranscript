import json
from fbtranscript.engines import hosted


def test_discovery_filters_non_asr_and_ranks_multilingual_for_arabic(monkeypatch):
    payloads = [
        {"data": [{"id": "nvidia/parakeet-tdt-0.6b-v2"},
                  {"id": "nvidia/canary-1b-asr"},
                  {"id": "nvidia/whisper-large-v3"},
                  {"id": "nvidia/magpie-tts"}]},
        {},
    ]
    monkeypatch.setattr(hosted, "_http_json", lambda url, key: payloads.pop(0))
    models = hosted.discover_asr_models("https://nim.example", "secret", "ar")
    assert [m["family"] for m in models] == ["whisper", "canary"]


def test_discovery_accepts_model_specific_unknown_asr_endpoint(monkeypatch):
    payloads = [{"data": [{"id": "unknown"}]}, {}]
    monkeypatch.setattr(hosted, "_http_json", lambda url, key: payloads.pop(0))
    models = hosted.discover_asr_models("https://nim.example", "secret", "ar")
    assert models == [{"id": None, "family": "deployed-asr", "rank": 100}]


def test_discovery_does_not_claim_global_catalog(monkeypatch):
    payloads = [{}, {}]
    monkeypatch.setattr(hosted, "_http_json", lambda url, key: payloads.pop(0))
    assert hosted.discover_asr_models("https://my-configured-nim", "secret", "ar") == [
        {"id": None, "family": "configured-asr-endpoint", "rank": 100}
    ]


def test_endpoint_url_normalization():
    assert hosted._api_url("https://nim.example/v1", "/v1/audio/transcriptions") == "https://nim.example/v1/audio/transcriptions"
    assert hosted._api_url("https://nim.example", "/v1/audio/transcriptions") == "https://nim.example/v1/audio/transcriptions"


def test_discovery_reads_speech_nim_metadata_model_profile(monkeypatch):
    payloads = [
        {"data": [{"id": "unknown"}]},
        {"modelInfo": [{"shortName": "parakeet-1-1b-ctc-riva:latest"}]},
    ]
    monkeypatch.setattr(hosted, "_http_json", lambda url, key: payloads.pop(0))
    models = hosted.discover_asr_models("https://nim.example", "secret", "en")
    assert models == [{"id": "parakeet-1-1b-ctc-riva:latest",
                       "family": "parakeet-ctc", "rank": 31}]
