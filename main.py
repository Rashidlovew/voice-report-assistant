import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

# Field prompts for conversation
field_prompts = [
    "مرحباً، كيف حالك اليوم؟",
    "أخبرني عن تاريخ الواقعة.",
    "ما الذي لاحظته في موقع الحادث؟",
    "ما هي نتيجة الفحص الفني؟",
    "ما هي النتائج التي توصلت إليها؟",
    "ما هو رأيك الفني النهائي؟"
]
user_state = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/fieldPrompt", methods=["GET"])
def field_prompt():
    user_id = request.remote_addr
    index = user_state.get(user_id, 0)
    
    if index < len(field_prompts):
        prompt = field_prompts[index]
        user_state[user_id] = index + 1
    else:
        prompt = "تم الانتهاء من جميع الأسئلة. شكراً لك!"

    audio = speak_text(prompt)
    return jsonify({
        "prompt": prompt,
        "audio": f"data:audio/mp3;base64,{base64.b64encode(audio).decode()}"
    })

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        data = request.get_json()
        audio_data = data["audio"]
        audio_base64 = audio_data.split(",")[1]
        audio_bytes = base64.b64decode(audio_base64)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        wav_path = temp_path.replace(".webm", ".wav")
        sound = AudioSegment.from_file(temp_path)
        sound.export(wav_path, format="wav")

        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        return jsonify({"transcript": transcript, "response": f"شكرًا على ردك: {transcript}"})
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
            "voice_settings": {
                "stability": 0.4,
                "similarity_boost": 0.75
            },
            "model_id": "eleven_multilingual_v2",
            "output_format": "mp3_44100_128"  # ✅ MP3 compatible format
        }
    )
    return response.content


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
