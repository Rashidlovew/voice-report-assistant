import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from pydub import AudioSegment
import requests

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

@app.route("/")
def index():
    return send_file("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_data = data.get("audio", "")
    if not audio_data or "," not in audio_data:
        return jsonify({"error": "Invalid audio format"}), 400

    try:
        audio_bytes = base64.b64decode(audio_data.split(",")[1])
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio_bytes)
            temp_path = f.name

        audio = AudioSegment.from_file(temp_path)
        wav_path = temp_path.replace(".webm", ".wav")
        audio.export(wav_path, format="wav")

        with open(wav_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f
            ).text

        return jsonify({ "transcript": transcript })

    except Exception as e:
        return jsonify({ "error": str(e) }), 500

@app.route("/fieldPrompt", methods=["GET"])
def field_prompt():
    text = "أرسل تاريخ الواقعة."
    audio_data = speak_text(text)
    return jsonify({
        "prompt": text,
        "audio": f"data:audio/mpeg;base64,{base64.b64encode(audio_data).decode()}"
    })

def speak_text(text):
    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/jN1a8k1Wv56Yf63YzCYr/stream",
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        },
        json={
            "text": text,
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.75},
            "output_format": "mp3_44100_128"
        }
    )
    return response.content

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
