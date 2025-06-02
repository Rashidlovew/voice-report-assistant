
```python
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import tempfile
import requests

app = Flask(__name__)
CORS(app)

ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY")
VOICE_ID = os.environ.get("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_from_directory("static", filename)

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files['audio']

    # Save temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    # Transcribe (replace with Whisper/OpenAI later if needed)
    transcript = "You said something."

    # Generate TTS
    tts_response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json",
        },
        json={
            "text": transcript,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
    )

    if tts_response.status_code != 200:
        return jsonify({"error": "TTS failed"}), 500

    audio_path = os.path.join("static", "response.mp3")
    with open(audio_path, "wb") as f:
        f.write(tts_response.content)

    return jsonify({
        "text": transcript,
        "audio_url": "/static/response.mp3"
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
