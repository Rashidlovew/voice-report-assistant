import os
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
from openai import OpenAI

app = Flask(__name__)

# Config
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Arabic field prompts
field_prompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و إجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
}
field_keys = list(field_prompts.keys())
user_state = {"step": 0, "responses": {}}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    user_state["step"] = 0
    user_state["responses"] = {}
    return jsonify({"message": "started"})

@app.route("/fieldPrompt", methods=["GET"])
def field_prompt():
    step = user_state["step"]
    if step >= len(field_keys):
        return jsonify({"done": True})

    field = field_keys[step]
    prompt = field_prompts[field]

    # Get voice from ElevenLabs
    audio = speak_text(prompt)
    return audio_response(audio)

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
    return response.content

def audio_response(audio_bytes):
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    with open(temp_path.name, "wb") as f:
        f.write(audio_bytes)
    try:
        audio = AudioSegment.from_file(temp_path.name, format="mp3")
    except Exception as e:
        print("⚠️ Error decoding MP3:", e)
        return jsonify({"error": "audio playback failed"}), 500
    return app.response_class(audio.export(format="mp3"), mimetype="audio/mpeg")

@app.route("/voice", methods=["POST"])
def handle_voice():
    audio_file = request.files["audio"]
    audio_path = os.path.join(tempfile.gettempdir(), "input.wav")
    audio_file.save(audio_path)

    # Whisper transcription
    with open(audio_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ar"
        )
    transcript_text = transcript.text.strip()

    step = user_state["step"]
    if step < len(field_keys):
        field = field_keys[step]
        user_state["responses"][field] = transcript_text
        user_state["step"] += 1

    return jsonify({"transcript": transcript_text})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
