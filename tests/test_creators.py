"""Contract tests use mocked AI responses; no requests or charges are sent to ElevenLabs."""
from pathlib import Path
from unittest.mock import patch
import json
import httpx
from fastapi.testclient import TestClient
import elevenlabs_client
from app import app

ROOT = Path(__file__).resolve().parents[1]
client = TestClient(app)


def test_independent_music_sound_effect_contracts(monkeypatch, tmp_path):
    monkeypatch.setenv('ELEVENLABS_API_KEY', 'test-do-not-use')
    calls = []

    class MockClient:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, *, headers, json):
            calls.append((url, json))
            return httpx.Response(200, content=b'ID3' + b'A' * 100)

    monkeypatch.setattr(elevenlabs_client.httpx, 'Client', MockClient)
    music_file = tmp_path / 'music.mp3'
    sfx_file = tmp_path / 'sfx.mp3'
    elevenlabs_client.create_text_music('Ambient synth music', music_file, duration_seconds=30)
    elevenlabs_client.create_sound_effect('A mechanical door opens', sfx_file, duration_seconds=4, loop=True)
    assert music_file.read_bytes().startswith(b'ID3')
    assert sfx_file.read_bytes().startswith(b'ID3')
    assert calls[0][0].endswith('/v1/music')
    assert calls[0][1] == {'prompt':'Ambient synth music','model_id':'music_v2_5','music_length_ms':30000,'force_instrumental':True}
    assert calls[1][0].endswith('/v1/sound-generation')
    assert calls[1][1]['model_id'] == 'eleven_text_to_sound_v3'
    assert calls[1][1]['loop'] is True
    assert 'music_length_ms' not in calls[1][1]


def test_independent_generation_requires_no_video(monkeypatch):
    samples = ROOT / 'samples' / 'sample_music.mp3'
    assert samples.is_file()

    def fake_music(prompt, output, *, duration_seconds, instrumental):
        output.write_bytes(samples.read_bytes())

    def fake_sfx(prompt, output, *, duration_seconds, loop):
        output.write_bytes(samples.read_bytes())

    with patch('app.create_text_music', fake_music), patch('app.create_sound_effect', fake_sfx):
        music = client.post('/api/create/music', json={ 'prompt': 'Warm piano for 30 seconds', 'duration_seconds': 30 })
        assert music.status_code == 200, music.text
        assert music.json()['kind'] == 'music'
        sound = client.post('/api/create/sfx', json={ 'prompt': 'Rain falling on roof', 'duration_seconds': 5 })
        assert sound.status_code == 200, sound.text
        assert sound.json()['kind'] == 'sfx'
        assert music.json()['id'] != sound.json()['id']
        assert client.get(music.json()['url']).content[:3] == b'ID3'
        assert client.get(sound.json()['url']).content[:3] == b'ID3'
        assert client.get(sound.json()['download_url']).status_code == 200
        assert client.get('/api/assets/../../unknown').status_code in (404,422)
        # Neither operation should create a video editing job.
        assert 'job_id' not in music.json()
        assert 'job_id' not in sound.json()


def test_creator_validation():
    assert client.post('/api/create/music', json={'prompt': 'hi', 'duration_seconds': 30}).status_code == 422
    assert client.post('/api/create/music', json={'prompt': 'nice', 'duration_seconds': 2}).status_code == 422
    assert client.post('/api/create/sfx', json={'prompt': 'thunder', 'duration_seconds': 31}).status_code == 422
    assert client.get('/api/assets/not-valid').status_code == 404
