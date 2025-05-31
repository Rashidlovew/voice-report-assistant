from flask import Flask, request, send_file, jsonify, send_from_directory
import openai
import os
import requests
import tempfile
from pydub import AudioSegment

app = Flask(__name__, static_url_path='', static_folder='static')


# API Keys from environment variables (Render)
openai.api_key = os.environ["OPENAI_KEY"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_KEY"]

# Serve the index.html from static/
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Transcribe Arabic audio using Whisper
def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file, language="ar")
    return transcript["text"]

# Rephrase text using GPT-4 in formal Arabic
def rephrase_with_gpt(text):
    prompt = f"أعد صياغة هذا النص ليكون مناسبًا لتقرير فحص جنائي دون إضافة مبالغات: {text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()

# Convert Arabic reply to voice using ElevenLabs
def generate_voice(text):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    voice_id = "EXAVITQu4vr4xnSDxMaL"  # Replace with Arabic voice ID if needed
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "voice_settings": {"stability": 0.3, "similarity_boost": 0.8}
    }

    response = requests.post(url, headers=headers, json=payload)
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_mp3.write(response.content)
    temp_mp3.flush()
    return temp_mp3.name

# Handle POST /voice with audio upload
@app.route('/voice', methods=['POST'])
def handle_voice():
    if 'audio' not in request.files:
        return jsonify({"error": "No audio file received"}), 400

    audio_file = request.files['audio']
    temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    audio_file.save(temp_input.name)

    audio = AudioSegment.from_file(temp_input.name)
    temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    audio.export(temp_wav.name, format="wav")

    transcript = transcribe_audio(temp_wav.name)
    rephrased = rephrase_with_gpt(transcript)
    voice_path = generate_voice(rephrased)

    return send_file(voice_path, mimetype="audio/mpeg")

# Start the Flask server
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
