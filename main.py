import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

from openai import OpenAI
from pydub import AudioSegment

app = Flask(__name__)
CORS(app)

# Load API keys from environment variables
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

user_state = {
    "current_field": "Date"
}

field_prompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    user_state["current_field"] = "Date"
    return jsonify({"status": "started", "nextPrompt": field_prompts["Date"]})

@app.route("/fieldPrompt", methods=["GET"])
def field_prompt():
    field = user_state["current_field"]
    prompt = field_prompts.get(field, "🎙️ Please speak...")
    audio_data = speak_text(prompt)
    audio_base64 = base64.b64encode(audio_data).decode()
    return jsonify({
        "prompt": prompt,
        "audio": f"data:audio/mpeg;base64,{audio_base64}"
    })

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        audio_data = request.json.get("audio")
        audio_base64 = audio_data.split(",")[1]
        audio_bytes = base64.b64decode(audio_base64)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
            temp_audio.write(audio_bytes)
            temp_audio.flush()
            temp_path = temp_audio.name

        audio = AudioSegment.from_file(temp_path)
        wav_path = temp_path.replace(".webm", ".wav")
        audio.export(wav_path, format="wav")

        with open(wav_path, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text",
                language="ar"
            )

        current_field = user_state["current_field"]
        user_state["last_input"] = transcript

        # Move to next field
        fields = list(field_prompts.keys())
        current_index = fields.index(current_field)
        if current_index + 1 < len(fields):
            user_state["current_field"] = fields[current_index + 1]
            next_field = user_state["current_field"]
            next_prompt = field_prompts[next_field]
        else:
            next_prompt = "✅ All fields collected."

        return jsonify({
            "transcript": transcript,
            "nextPrompt": next_prompt
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

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
