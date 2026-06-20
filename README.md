# Nayan

Assistive navigation backend: fetch camera snapshots, analyze them with a vision LLM, and speak guidance via TTS.

## Architecture

```
app/
├── main.py           # FastAPI app and service lifecycle
├── config.py         # Environment-based settings
├── api.py            # HTTP routes
├── camera_client.py  # IP camera snapshot proxy (httpx)
├── vision.py         # Groq vision / navigation guidance
├── tts.py            # Priority TTS worker (edge-tts)
├── images.py         # Image resize/rotate helpers
└── prompts.py        # Prompt template loader

assets/prompts/
└── navigation.md     # Navigation guidance prompt (no hardcoded prompts in code)
```

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Install ffmpeg for audio playback (required by pydub):

- macOS: `brew install ffmpeg`
- Linux: `sudo apt install ffmpeg`

Create a `.env` file:

```env
CAMERA_URL=http://192.168.1.25:8080/photo.jpg
TIMEOUT_SECONDS=3
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=meta-llama/llama-4-scout-17b-16e-instruct
TTS_VOICE=en-US-JennyNeural
TTS_RATE=0.5
```

## Run

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

API docs: http://localhost:8000/docs

## Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Service, camera, vision, and TTS status |
| `GET /snapshot` | Raw JPEG bytes from the IP camera |
| `GET /describe` | Camera snapshot → Groq navigation JSON |
| `GET /navigate?speak=true` | Describe + optionally queue TTS |
| `POST /speak` | Queue `{ "text": "...", "action": "STOP" }` for speech |

Example polling loop (every ~2 seconds):

```bash
curl "http://localhost:8000/navigate?speak=true"
```

## Tests

```bash
pytest
```
