import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

# Load keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        data = request.get_json()
        audio_data = data.get("audio", "")
        if not audio_data or "," not in audio_data:
            return jsonify({"error": "Invalid audio format"}), 400

        audio_base64 = audio_data.split(",")[1]
        audio_bytes = base64.b64decode(audio_base64)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
            temp_webm.write(audio_bytes)
            webm_path = temp_webm.name

        wav_path = webm_path.replace(".webm", ".wav")
        sound = AudioSegment.from_file(webm_path)
        sound.export(wav_path, format="wav")

        with open(wav_path, "rb") as f:
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )

        ai_reply = f"تم استلام ما قلت: {transcription.strip()}، هل ترغب بالاستمرار؟"
        spoken_audio = speak_text(ai_reply)

        return jsonify({
            "transcript": transcription.strip(),
            "response": ai_reply,
            "audio": base64.b64encode(spoken_audio).decode()
        })

    except Exception as e:
        print("❌ Error in /submitAudio:", str(e))
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
