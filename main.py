import os
import base64
import tempfile
from flask import Flask, request, send_from_directory, jsonify
import requests
from openai import OpenAI

# Environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")  # Change if needed

# Clients
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Flask app
app = Flask(__name__, static_url_path="", static_folder="static")

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file"}), 400

    audio_file = request.files['audio']

    # Save temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp_audio:
        audio_path = tmp_audio.name
        audio_file.save(audio_path)

    # Transcribe with Whisper
    with open(audio_path, "rb") as f:
        transcription = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ar"
        )

    text = transcription.text.strip()
    print("🎙️ Transcribed:", text)

    # Rephrase with GPT
    chat_response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أنت مساعد صوتي ذكي تعيد صياغة الجمل العربية لتكون احترافية ولطيفة."},
            {"role": "user", "content": text}
        ]
    )
    improved_text = chat_response.choices[0].message.content.strip()
    print("🤖 GPT:", improved_text)

    # Get audio from ElevenLabs
    audio_response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "accept": "audio/mpeg",
            "Content-Type": "application/json"
        },
        json={
            "text": improved_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.9,
                "style": 0.5,
                "use_speaker_boost": True
            }
        }
    )

    if audio_response.status_code != 200:
        print("❌ ElevenLabs error:", audio_response.text)
        return jsonify({"error": "Failed to generate audio"}), 500

    audio_data = audio_response.content
    print("✅ Audio size:", len(audio_data))

    # Base64 encode to return
    encoded_audio = base64.b64encode(audio_data).decode("utf-8")
    return jsonify({
        "text": improved_text,
        "audio": f"data:audio/mpeg;base64,{encoded_audio}"
    })

@app.route("/static/<path:path>")
def serve_static(path):
    return send_from_directory("static", path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
