from flask import Flask, request, send_file, jsonify
import openai
import os
import requests
import tempfile
from pydub import AudioSegment

# Configure Flask to serve static files from /static
app = Flask(__name__, static_url_path='', static_folder='static')

# Load API keys from environment
openai.api_key = os.environ["OPENAI_KEY"]
ELEVENLABS_API_KEY = os.environ["ELEVENLABS_KEY"]

# Serve index.html
@app.route('/')
def index():
    return app.send_static_file('index.html')


# Whisper Transcription
def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file, language="ar")
    return transcript["text"]


# GPT Rephrasing
def rephrase_with_gpt(text):
    prompt = f"أعد صياغة هذا النص ليكون مناسبًا لتقرير فحص جنائي دون إضافة مبالغات: {text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# ElevenLabs TTS
def generate_voice(text):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    voice_id = "EXAVITQu4vr4xnSDxMaL"  # Default voice, replace if needed
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = {
        "text": text,
        "voice_settings": {"stability": 0.3, "similarity_boost": 0.8}
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code != 200:
        raise Exception(f"ElevenLabs Error: {response.status_code}, {response.text}")

    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_mp3.write(response.content)
    temp_mp3.flush()
    return temp_mp3.name


# Handle /voice POST request
@app.route('/voice', methods=['POST'])
def handle_voice():
    try:
        if 'audio' not in request.files:
            return jsonify({"error": "No audio file received"}), 400

        audio_file = request.files['audio']
        temp_input = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
        audio_file.save(temp_input.name)

        audio = AudioSegment.from_file(temp_input.name)
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        audio.export(temp_wav.name, format="wav")

        transcript = transcribe_audio(temp_wav.name)
        print("📝 Transcript:", transcript)

        rephrased = rephrase_with_gpt(transcript)
        print("✍️ Rephrased:", rephrased)

        voice_path = generate_voice(rephrased)
        print("🔊 Voice path:", voice_path)

        return send_file(voice_path, mimetype="audio/mpeg")

    except Exception as e:
        print(f"💥 ERROR in /voice: {e}")
        return jsonify({"error": str(e)}), 500


# Start the app on Render (uses PORT environment variable)
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
