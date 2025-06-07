import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, play, save, set_api_key

app = Flask(__name__)
CORS(app)

# Set API Keys
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# Session storage
user_session = {
    "current_field": "Date",
    "fields": {},
}

# Arabic prompts
field_prompts = {
    "Date": "🎙️ أخبرني عن تاريخ الواقعة.",
    "Briefing": "🎙️ ما هو موجز الواقعة؟",
    "LocationObservations": "🎙️ ماذا لاحظت عند معاينة الموقع؟",
    "Examination": "🎙️ ما هي نتيجة الفحص الفني؟",
    "Outcomes": "🎙️ ما هي النتيجة النهائية بعد الفحص؟",
    "TechincalOpinion": "🎙️ ما هو رأيك الفني؟"
}
field_order = list(field_prompts.keys())

# Stream TTS reply using ElevenLabs
@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    audio = generate(text=text, voice="Rachel", model="eleven_multilingual_v2")
    temp_path = tempfile.mktemp(suffix=".mp3")
    save(audio, temp_path)
    return send_file(temp_path, mimetype="audio/mpeg")

# Transcribe and respond
@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_b64 = data.get("audio")
    if not audio_b64:
        return jsonify({
            "response": field_prompts[user_session["current_field"]],
            "action": "continue",
            "transcript": ""
        })

    audio_data = base64.b64decode(audio_b64.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_data)
        f.flush()
        audio_path = f.name

    # Whisper transcription
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=open(audio_path, "rb"),
        language="ar"
    )
    transcript = result.text

    # Rephrase via GPT
    field = user_session["current_field"]
    gpt_result = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أعد صياغة هذه الجملة بالعربية بشكل مهني لتوضع ضمن تقرير رسمي:"},
            {"role": "user", "content": transcript}
        ]
    )
    rephrased = gpt_result.choices[0].message.content.strip()
    user_session["fields"][field] = rephrased

    # Move to next field
    next_index = field_order.index(field) + 1
    if next_index < len(field_order):
        next_field = field_order[next_index]
        user_session["current_field"] = next_field
        response_text = field_prompts[next_field]
        return jsonify({
            "response": response_text,
            "action": "continue",
            "transcript": rephrased
        })
    else:
        # Final message
        return jsonify({
            "response": "✅ تم استلام جميع البيانات. يتم الآن تجهيز التقرير.",
            "action": "done",
            "transcript": rephrased
        })

@app.route("/")
def home():
    return "👮 Voice Assistant is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
