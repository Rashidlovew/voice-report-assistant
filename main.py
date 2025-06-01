import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

# Load API keys from environment
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
        audio_data = data["audio"]
        if "," in audio_data:
            audio_base64 = audio_data.split(",")[1]
        else:
            return jsonify({"error": "Invalid audio format"}), 400

        audio_bytes = base64.b64decode(audio_base64)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        # Convert to wav for Whisper
        wav_path = temp_path.replace(".webm", ".wav")
        sound = AudioSegment.from_file(temp_path)
        sound.export(wav_path, format="wav")

        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        # Enhance the Arabic transcript using GPT-4
        gpt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Arabic-speaking police assistant."},
                {"role": "user", "content": "النص المُرسل: " + transcript.strip()}
            ]
        )
        enhanced_text = gpt_response.choices[0].message.content.strip()

        # Get audio reply from ElevenLabs (streaming)
        audio_mp3 = stream_speech(enhanced_text)

        return jsonify({
            "transcript": transcript.strip(),
            "response": enhanced_text,
            "audio": base64.b64encode(audio_mp3).decode("utf-8")
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fieldPrompt")
def field_prompt():
    text = request.args.get("text", "مرحباً، كيف حالك اليوم؟")
    audio = stream_speech(text)
    return jsonify({
        "prompt": text,
        "audio": f"data:audio/mpeg;base64,{base64.b64encode(audio).decode()}"
    })

def stream_speech(text):
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
                "stability": 0.3,
                "similarity_boost": 0.75
            }
        }
    )
    return response.content

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
