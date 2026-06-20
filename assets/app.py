import io
import os
import time
import base64
from dotenv import load_dotenv
import cv2
from PIL import Image
import pyaudio
from groq import Groq

# 1. Configuration Setup
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
client = Groq(api_key=GROQ_API_KEY)

# 2. Audio Hardware Configuration (PCM 24kHz matches Groq TTS engine outputs)
p = pyaudio.PyAudio()
audio_stream = p.open(format=pyaudio.paInt16, channels=1, rate=24000, output=True)

def process_and_speak(frame):
    """Encodes a video frame, gets a navigation command from Groq, and plays the audio."""
    # Convert OpenCV image array (BGR) to PIL Image format (RGB)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_frame)
    
    # Compress image to optimize cellular or home wifi upload speeds
    pil_img.thumbnail((600, 600))
    buffered = io.BytesIO()
    pil_img.save(buffered, format="JPEG")
    base64_image = base64.b64encode(buffered.getvalue()).decode('utf-8')
    
    print("\n🧠 Sending camera frame to Llama Vision...")
    vision_prompt = (
        "You are an assistant for a blind person. Look at this camera view. "
        "State the closest main obstacle and give a short action instruction. "
        "Keep your answer under 5 words total! Example: 'Chair ahead. Walk left.'"
    )
    
    try:
        # Request scene reasoning from Groq's high-speed vision model
        chat_completion = client.chat.completions.create(
            model="meta-llama/llama-4-scout-17b-16e-instruct",

            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": vision_prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            max_tokens=20
        )
        
        navigation_text = chat_completion.choices[0].message.content

        print(f"📡 AI Instruction: '{navigation_text}'")
        
        # Turn text into navigation voice commands instantly
        tts_response = client.audio.speech.create(
            model="canopylabs/orpheus-v1-english",
            voice="austin",
            input=navigation_text,
            response_format="wav"
        )
        
        print("🔊 Playing warning audio chunk...")
        audio_stream.write(tts_response.read())

        
    except Exception as e:
        print(f"⚠️ Error running API loop: {e}")

def main_camera_loop():
    print("📹 Starting camera system... Press 'q' inside the video window to stop.")
    
    # 0 is usually your built-in laptop webcam or primary USB camera
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Could not detect or open any system camera.")
        return

    last_check_time = 0
    # Every 4 seconds, the system takes a frame and reads it out loud
    check_interval = 4.0 

    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Dropped video frame. Retrying...")
            continue
            
        # Display the live window for testing feedback
        cv2.imshow("Blind Assistant Vision - Testing Window", frame)
        
        current_time = time.time()
        if current_time - last_check_time > check_interval:
            # Run our analysis function
            process_and_speak(frame)
            last_check_time = current_time
            
        # Break loop if user focuses video box and hits 'q' key
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    # Clean up device configurations on program exit
    cap.release()
    cv2.destroyAllWindows()
    audio_stream.stop_stream()
    audio_stream.close()
    p.terminate()
    print("✅ System: Camera monitoring loop closed down cleanly.")

if __name__ == "__main__":
    main_camera_loop()
