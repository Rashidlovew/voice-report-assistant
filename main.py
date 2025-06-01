import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import requests

app = Flask(__name__)
CORS(app)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

field_prompts = [
    "🎙️ أرسل تاريخ الواقعة.",
    "🎙️ أرسل موجز الواقعة.",
    "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "🎙️ أرسل الرأي الفني."
]

state = {"step": 0}

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/static/script.js")
def script():
    return send_from_directory("static", "script.js")

@app.route("/start", methods=["POST"])
def start():
    state["step"] = 0
    return jsonify({"message": "بدأنا!", "done": False})

@app.route("/fieldPrompt", methods=["GET"])
def field_prompt():
    step = state["step"]
    if step >= len(field_prompts):
        return jsonify({"done": True})
    prompt = field_prompts[step]
    audio = speak_text(prompt)
    return jsonify({"text": prompt, "audio": audio, "done": False})

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_data = data.get("audio", "")
    
    if "," not in audio_data:
        return jsonify({"error": "Invalid audio data"}), 400

    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
        temp_file.write(audio_bytes)
        temp_path = temp_file.name

    audio_file = open(temp_path, "rb")
    transcript = client.audio.transcriptions.create(
        file=audio_file,
        model="whisper-1",
        language="ar"
    ).text

    step = state["step"]
    state["step"] += 1
    return jsonify({"text": transcript, "done": step >= len(field_prompts)})

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
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            "output_format": "mp3_44100_128"
        }
    )
    return base64.b64encode(response.content).decode("utf-8")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
