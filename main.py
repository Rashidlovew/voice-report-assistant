# ✅ main.py (Non-streaming working version)
import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

def generate_speech(text):
    url = "https://api.elevenlabs.io/v1/text-to-speech/jN1a8k1Wv56Yf63YzCYr"
    headers = {
        "xi-api-key": ELEVENLABS_KEY,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg"
    }
    payload = {
        "text": text,
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 0.75
        },
        "output_format": "mp3_44100_128"
    }
    response = requests.post(url, headers=headers, json=payload)
    return response.content

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def handle_audio():
    try:
        data = request.get_json()
        audio_data = data["audio"]
        if "," in audio_data:
            audio_base64 = audio_data.split(",")[1]
        else:
            audio_base64 = audio_data

        audio_bytes = base64.b64decode(audio_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio_bytes)
            webm_path = f.name

        wav_path = webm_path.replace(".webm", ".wav")
        AudioSegment.from_file(webm_path).export(wav_path, format="wav")

        with open(wav_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )

        user_text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()

        gpt_reply = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "أنت مساعد صوتي يتحدث العربية ويقدم ردوداً بشرية"},
                {"role": "user", "content": user_text}
            ]
        )
        final_text = gpt_reply.choices[0].message.content.strip()

        audio_output = generate_speech(final_text)
        with open("test_response.mp3", "wb") as f:
            f.write(audio_output)

        return jsonify({
            "transcript": user_text,
            "response": final_text,
            "audio": base64.b64encode(audio_output).decode("utf-8")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download-audio")
def download():
    if os.path.exists("test_response.mp3"):
        return send_file("test_response.mp3", mimetype="audio/mpeg")
    return "No file found.", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
