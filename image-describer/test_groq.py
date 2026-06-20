"""
test_groq.py

Live assistive-navigation pipeline using Groq's vision model (Llama 4 Scout):
  1. Start the capture service (grabs camera frames on an interval)
  2. Repeatedly fetch the latest frame as bytes
  3. Send to Groq with a navigation-action prompt
  4. Print the resulting action + speech_text, ready for a TTS module
"""

import os
import json
import time
import base64
from io import BytesIO

from dotenv import load_dotenv
from groq import Groq
from PIL import Image
import requests

from text_to_speech import TTSEngine
# import tts/
import logging

logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# --- Setup ---
load_dotenv()

API_KEY = os.getenv("GROQ_API_KEY")
if not API_KEY or API_KEY == "your_key_here":
    raise ValueError(
        "GROQ_API_KEY not set. Add your real key to the .env file."
    )

client = Groq(api_key=API_KEY)

# Groq hosts open vision models on their fast inference hardware — this
# is not Groq's own model, it's Llama 4 Scout running on Groq's LPUs.
# Check https://console.groq.com/docs/models for current vision model names,
# since availability/naming changes as Groq adds new hosted models.
MODEL_NAME = "meta-llama/llama-4-scout-17b-16e-instruct"

# --- Live capture service config ---
# The capture service (run by the other developer / your camera module)
# exposes two endpoints:
#   POST /capture/start  -> tells it to start grabbing frames on an interval
#   GET  /frame/latest   -> returns the most recent captured frame as raw bytes
# CAPTURE_START_URL = "http://localhost:8000/capture/start"
LATEST_FRAME_URL = "http://192.168.103.180:8080/photo.jpg"  # ← YOUR CAMERA SERVICE URL
# CAPTURE_PAYLOAD = {"camera_url": "http://192.168.103.180:8080", "interval_seconds": 5}

POLL_INTERVAL_SECONDS = 1  # how often WE ask for a new frame + describe it


def start_capture_service() -> None:
    """Tell the capture service to begin grabbing frames. Call this once,
    before entering the polling loop — not every iteration."""
    response = requests.post(CAPTURE_START_URL, json=CAPTURE_PAYLOAD)
    response.raise_for_status()  # fail loudly if the capture service rejects this


def fetch_latest_frame_bytes() -> bytes:
    """Fetch the most recent frame from the capture service as raw bytes.
    Note: .content (not the Response object itself) gives the actual
    image bytes — requests.get() returns a Response wrapper, not bytes."""
    response = requests.get(LATEST_FRAME_URL)
    with open('latest.png',"wb") as f:
        f.write(response.content)
    response.raise_for_status()
    return response.content

# Same prompt as test_gemini.py, so results are directly comparable.
PROMPT = """
You are assisting a blind person navigating their environment using a camera
that takes a photo every 10 seconds. Analyze the image and respond with ONLY
a JSON object (no markdown, no extra text) with exactly these fields:

{
  "action": one of ["STOP", "TURN_SLIGHT_LEFT", "TURN_SLIGHT_RIGHT", "TURN_LEFT", "TURN_RIGHT", "SLOW_DOWN", "CONTINUE"],
  "speech_text": a short, natural sentence (under 10 words) suitable for
                  text-to-speech, telling the person what to do right now,
                  e.g. "Stop, no space to pass." or "Turn slightly left, continue."
}

Decision rules:
- Judge whether an average adult could physically fit through the open space
  in the path, considering obstacle width relative to typical shoulder width.
- If there is enough clear space to pass by adjusting course slightly, choose
  TURN_SLIGHT_LEFT or TURN_SLIGHT_RIGHT (whichever side has more open space)
  and keep speech_text encouraging forward movement, e.g. "Turn slightly left, then continue."
- If a full turn is needed to find a path (no slight adjustment works), choose
  TURN_LEFT or TURN_RIGHT.
- If there is no usable space to pass at all (blocked path, wall, drop-off,
  dangerous hazard), choose STOP.
- If moving but caution is warranted (uneven ground, approaching but not blocking
  obstacle), choose SLOW_DOWN.
- If the path is clearly clear, choose CONTINUE with speech_text "Path is clear."
- Do not mention distances, object names, or directions other than left/right
  in speech_text unless essential — keep it action-first and brief.
"""

# Resize before sending — large camera-resolution images get internally
# tiled/processed in more detail than needed, which adds latency. The model
# doesn't need full resolution to judge "is there space to pass."
MAX_DIMENSION = 512  # pixels, longest side


def rotate_image_clockwise(img: Image.Image, degrees: int = 90) -> Image.Image:
    """Rotate the image clockwise by the given degrees.

    PIL's Image.rotate() rotates counter-clockwise for positive angles,
    so we negate the value to get clockwise rotation instead.
    expand=True keeps the full image (otherwise PIL crops corners that
    fall outside the original width/height after rotation).
    """
    return img.rotate(-degrees, expand=True)


def resize_image(img: Image.Image, max_dimension: int = MAX_DIMENSION) -> Image.Image:
    """Resize image so its longest side is max_dimension, preserving aspect ratio."""
    width, height = img.size
    if max(width, height) <= max_dimension:
        return img

    if width >= height:
        new_width = max_dimension
        new_height = int(height * (max_dimension / width))
    else:
        new_height = max_dimension
        new_width = int(width * (max_dimension / height))

    return img.resize((new_width, new_height), Image.LANCZOS)


def image_to_data_url(img: Image.Image) -> str:
    """Encode a PIL image as a base64 data URL, which is how Groq's
    OpenAI-compatible API expects image input."""
    buffer = BytesIO()
    img.convert("RGB").save(buffer, format="JPEG")
    encoded = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"


def describe_image_bytes(image_bytes: bytes) -> tuple[dict, float]:
    """Send raw image bytes to Groq and return (parsed_json_dict, time_taken_seconds).

    Takes bytes straight from the capture service, with no file I/O involved.
    """
    img = Image.open(BytesIO(image_bytes))
    img = rotate_image_clockwise(img, degrees=90)
    img.save("latest.png")
    img = resize_image(img)
    data_url = image_to_data_url(img)

    start = time.time()
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": PROMPT},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        response_format={"type": "json_object"},
        max_tokens=150,
    )
    elapsed = time.time() - start

    raw_text = response.choices[0].message.content.strip()
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        cleaned = raw_text.strip("`").removeprefix("json").strip()
        parsed = json.loads(cleaned)

    return parsed, elapsed


def run_live_loop():
    """The assistive-device pipeline: start the capture service once, then
    repeatedly fetch the latest frame and describe it on an interval."""
    print("\nInitializing TTS engine...")
    tts = TTSEngine(voice="en-US-AriaNeural", rate=0.95)
    tts.start()
    print("✓ TTS engine started\n")
    print("Starting capture service...")
    # start_capture_service()

    print(f"Polling every {POLL_INTERVAL_SECONDS}s. Press Ctrl+C to stop.\n")
    try:
        while True:
            try:
                frame_bytes = fetch_latest_frame_bytes()
                data, elapsed = describe_image_bytes(frame_bytes)
                print(f"[{elapsed:.2f}s] action={data.get('action')} | speech_text={data.get('speech_text')}")
                # TODO: hand off data["speech_text"] to the TTS module here
                action = data.get("action", "CONTINUE")
                speech_text = data.get("speech_text", "")
                if speech_text:
                    tts.speak(speech_text, action)
            except Exception as e:
                # Don't let one bad frame/response kill the whole loop —
                # log it and keep going, since this runs unattended.
                print(f"ERROR on this cycle: {e}")

            time.sleep(POLL_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        print("\nStopped.")
    
    finally:
        tts.stop()
        print("TTS engine stopped.")


if __name__ == "__main__":
    run_live_loop()
