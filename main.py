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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    try:
        data = request.get_json()
        audio_data = data.get("audio", "")
        if "," in audio_data:
            audio_base64 = audio_data.split(",")[1]
        else:
            return jsonify({"error": "Invalid audio format"}), 400

        # Decode and save temporary audio file
        audio_bytes = base64.b64decode(audio_base64)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
            temp_file.write(audio_bytes)
            temp_path = temp_file.name

        # Convert to WAV
        wav_path = temp_path.replace(".webm", ".wav")
        sound = AudioSegment.from_file(temp_path)
        sound.export(wav_path, format="wav")

        # Transcribe with Whisper
        with open(wav_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )

        user_text = transcript.strip()

        # AI reply
        prompt = f"لدي النص التالي كملاحظة صوتية من محقق جنائي: '{user_text}'. من فضلك أعد صياغته بطريقة رسمية ومهنية كجزء من تقرير شرطة."
        gpt_response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        ai_text = gpt_response.choices[0].message.content.strip()

        # Generate voice
        audio = speak_text(ai_text)

        return jsonify({
            "transcript": user_text,
            "response": ai_text,
            "audio": base64.b64encode(audio).decode()
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/fieldPrompt")
def field_prompt():
    text = request.args.get("text", "مرحباً، كيف حالك اليوم؟")
    audio = speak_text(text)
    return jsonify({
        "prompt": text,
        "audio": f"data:audio/mpeg;base64,{base64.b64encode(audio).decode()}"
    })

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
