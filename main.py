import os
import base64
import tempfile
import requests
import json
import urllib3
from flask import Flask, request, jsonify, render_template, send_file
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
        audio_data = data["audio"]
        if "," in audio_data:
            audio_base64 = audio_data.split(",")[1]
        else:
            audio_base64 = audio_data

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

        audio_mp3 = stream_speech(enhanced_text)

        with open("test_response.mp3", "wb") as f:
            f.write(audio_mp3)

        print("✅ AUDIO SIZE:", len(audio_mp3), "bytes")

        return jsonify({
            "transcript": text,
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

@app.route("/download-audio")
def download_audio():
    filepath = "test_response.mp3"
    if os.path.exists(filepath):
        return send_file(filepath, mimetype="audio/mpeg", as_attachment=True)
    else:
        return "Audio not found", 404

# ✅ ElevenLabs streaming using urllib3
def stream_speech(text):
    http = urllib3.PoolManager()
    encoded_body = json.dumps({
        "text": text,
        "voice_settings": {
            "stability": 0.3,
            "similarity_boost": 0.75
        },
        "output_format": "mp3_44100_128"
    }).encode("utf-8")

    response = http.request(
        "POST",
        "https://api.elevenlabs.io/v1/text-to-speech/9BWtsMlNQrJLRac0k9x3/stream",  # Aria
        body=encoded_body,
        headers={
            "Content-Type": "application/json",
            "xi-api-key": ELEVENLABS_KEY,
            "Accept": "audio/mpeg"
        },
        preload_content=False
    )

    audio_data = b"".join(response.stream(4096))
    response.release_conn()

    return audio_data

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
