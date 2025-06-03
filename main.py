# main.py
import os
import base64
import tempfile
import requests
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel

client = OpenAI(api_key=OPENAI_API_KEY)
app = Flask(__name__, static_url_path='/static')
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        data = request.get_json()
        audio_base64 = data["audio"].split(",")[-1]
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

        text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()

        gpt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a helpful Arabic-speaking police assistant."},
                {"role": "user", "content": f"النص المُرسل: {text}"}
            ]
        )
        enhanced_text = gpt_response.choices[0].message.content.strip()

        return jsonify({
            "transcript": text,
            "response": enhanced_text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    return Response(elevenlabs_stream(text), mimetype="audio/mpeg")

def elevenlabs_stream(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}/stream"
    headers = {
        "xi-api-key": ELEVENLABS_KEY,
        "Accept": "audio/mpeg",
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 0.75
        }
    }
    r = requests.post(url, headers=headers, json=payload, stream=True)
    for chunk in r.iter_content(chunk_size=1024):
        if chunk:
            yield chunk

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
