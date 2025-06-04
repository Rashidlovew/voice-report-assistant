import os
import base64
import tempfile
import requests
import time
from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from pydub import AudioSegment
from openai import OpenAI

# API Keys and Voice Config
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")
VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__, static_url_path='/static')
CORS(app)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        t_start = time.time()

        # Decode audio
        data = request.get_json()
        audio_base64 = data["audio"].split(",")[-1]
        audio_bytes = base64.b64decode(audio_base64)

        # Save to temp .webm and convert to .wav
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        wav_path = temp_path.replace(".webm", ".wav")
        sound = AudioSegment.from_file(temp_path)
        sound.export(wav_path, format="wav")

        # Transcribe using Whisper
        with open(wav_path, "rb") as audio_file:
            t_whisper = time.time()
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
            t_whisper_done = time.time()

        text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()

        # Generate GPT response
        t_gpt = time.time()
        gpt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "أنت مساعد ذكي يتحدث اللغة العربية ويقدم ردوداً مختصرة بشكل مهني."},
                {"role": "user", "content": text}
            ]
        )
        enhanced_text = gpt_response.choices[0].message.content.strip()
        t_end = time.time()

        # Logs for performance
        print("📝 Whisper time:", round(t_whisper_done - t_whisper, 2), "sec")
        print("💬 GPT time:", round(t_end - t_gpt, 2), "sec")
        print("⏱️ Total:", round(t_end - t_start, 2), "sec")

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
            "stability": 0.2,  # Faster start (lower than 0.3)
            "similarity_boost": 0.75
        }
    }
    r = requests.post(url, headers=headers, json=payload, stream=True)
    for chunk in r.iter_content(chunk_size=1024):
        if chunk:
            yield chunk

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
