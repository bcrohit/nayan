"""
test_gemini.py

Purpose: Evaluate Gemini Flash for an assistive-tech use case —
describing obstacles/hazards in an image for a blind user, and
producing a structured, actionable signal (stop/turn/direction)
that a downstream text-to-speech module can consume directly.

Workflow per image:
  1. Load image from test_images/
  2. Send to Gemini with a structured-JSON navigation prompt
  3. Parse + print the structured result, and how long the call took
  4. Save results to output/results.txt for later comparison
"""

import os
import json
import time
from pathlib import Path

from dotenv import load_dotenv
import google.generativeai as genai
from PIL import Image

# --- Setup ---
load_dotenv()  # reads GEMINI_API_KEY from .env

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY or API_KEY == "your_key_here":
    raise ValueError(
        "GEMINI_API_KEY not set. Add your real key to the .env file."
    )

genai.configure(api_key=API_KEY)

MODEL_NAME = "gemini-2.5-flash"  # we can swap this later to compare models

# Forcing JSON output means the downstream TTS module gets clean,
# predictable fields instead of having to parse free-form sentences.
GENERATION_CONFIG = {
    "response_mime_type": "application/json",
}

model = genai.GenerativeModel(MODEL_NAME, generation_config=GENERATION_CONFIG)

# This prompt is the important part — it's written for the assistive-tech
# use case, not a generic "describe this image" caption. It forces a
# structured, actionable output instead of prose.
PROMPT = """
You are assisting a blind person navigating their environment using a camera
that takes a photo every 10 seconds. Analyze the image and respond with ONLY
a JSON object (no markdown, no extra text) with exactly these fields:

{
  "action": one of ["STOP", "TURN_LEFT", "TURN_RIGHT", "SLOW_DOWN", "CONTINUE"],
  "obstacle": short noun phrase naming the main obstacle/hazard, or null if none,
  "direction": one of ["ahead", "left", "right", "behind", null],
  "distance": one of ["near", "medium", "far", null] — a QUALITATIVE estimate only,
              never a precise number, since exact distance cannot be reliably
              judged from a single 2D image,
  "speech_text": a short, natural sentence (under 12 words) suitable for
                  text-to-speech, e.g. "Stop. Pothole ahead, two steps away."
}

Rules:
- If the path is clear, use action "CONTINUE", obstacle null, direction null,
  distance null, and speech_text "Path appears clear."
- Prioritize safety-relevant obstacles: people, vehicles, steps, curbs, holes,
  furniture, poles, open doors, drop-offs.
- Ignore colors, aesthetics, and irrelevant background details.
- "action" should reflect what the person should physically do right now.
"""

INPUT_DIR = Path("test_images")
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(exist_ok=True)


def describe_image(image_path: Path) -> tuple[dict, float]:
    """Send one image to Gemini and return (parsed_json_dict, time_taken_seconds)."""
    img = Image.open(image_path)

    start = time.time()
    response = model.generate_content([PROMPT, img])
    elapsed = time.time() - start

    raw_text = response.text.strip()
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError:
        # fallback in case the model wraps output in markdown fences or similar
        cleaned = raw_text.strip("`").removeprefix("json").strip()
        parsed = json.loads(cleaned)

    return parsed, elapsed


def main():
    image_files = sorted(
        [
            f
            for f in INPUT_DIR.iterdir()
            if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        ]
    )

    if not image_files:
        print(f"No images found in {INPUT_DIR}/. Add some test images first.")
        return

    results = []
    print(f"Testing {len(image_files)} image(s) with model: {MODEL_NAME}\n")

    for img_path in image_files:
        print(f"--- {img_path.name} ---")
        try:
            data, elapsed = describe_image(img_path)
            print(f"Time: {elapsed:.2f}s")
            print(f"  action:      {data.get('action')}")
            print(f"  obstacle:    {data.get('obstacle')}")
            print(f"  direction:   {data.get('direction')}")
            print(f"  distance:    {data.get('distance')}")
            print(f"  speech_text: {data.get('speech_text')}\n")

            results.append(
                f"{img_path.name} | {elapsed:.2f}s | {json.dumps(data)}"
            )
        except Exception as e:
            print(f"ERROR: {e}\n")
            results.append(f"{img_path.name} | ERROR | {e}")

    # Save results for later comparison against other models
    results_file = OUTPUT_DIR / "results.txt"
    with open(results_file, "w") as f:
        f.write(f"Model: {MODEL_NAME}\n\n")
        f.write("\n".join(results))

    print(f"Results saved to {results_file}")


if __name__ == "__main__":
    main()