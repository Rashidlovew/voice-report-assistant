from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import openai
import requests
import base64
import os
from io import BytesIO

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

@app.route("/")
def index():
    return "Voice Assistant is running."

@app.route("/submitAudio", methods=["POST"])
def handle_audio():
    file = request.files["audio"]
    audio_bytes = file.read()

    # Transcribe with OpenAI Whisper
    transcript = openai.Audio.transcribe("whisper-1", BytesIO(audio_bytes))
    user_text = transcript["text"]

    # Rephrase the transcribed text using GPT
    prompt = f"صِغ هذا بأسلوب تقرير شرطة رسمي: {user_text}"
    completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أنت مساعد تقارير جنائي محترف."},
            {"role": "user", "content": prompt}
        ]
    )
    rephrased_text = completion.choices[0].message.content

    # Synthesize voice with ElevenLabs
    tts_response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}",
        headers={
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        },
        json={
            "text": rephrased_text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 1,
                "use_speaker_boost": True
            }
        }
    )

    if tts_response.status_code != 200:
        print("TTS failed", tts_response.text)
        return jsonify({"text": rephrased_text, "audio": None})

    audio_data = tts_response.content
    print("Audio size:", len(audio_data))

    audio_base64 = base64.b64encode(audio_data).decode("utf-8")
    audio_src = f"data:audio/mpeg;base64,{audio_base64}"
    print("Audio base64 preview:", audio_src[:100])

    return jsonify({"text": rephrased_text, "audio": audio_src})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
