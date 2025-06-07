import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file, send_from_directory
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, Voice, VoiceSettings, set_api_key
from utils import transcribe_audio, rephrase_text, detect_intent, get_next_prompt, field_prompts, field_names_ar

app = Flask(__name__, static_url_path='/static')
CORS(app)

# إعداد API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# الجلسة
user_session = {
    "current_field": None,
    "fields": {},
    "awaiting_confirmation": False,
}

# تقديم index.html
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

# تهيئة الحديث الأول
@app.route("/next", methods=["GET"])
def next_step():
    if user_session["current_field"] is None:
        user_session["current_field"] = list(field_prompts.keys())[0]
    prompt = field_prompts[user_session["current_field"]]
    return jsonify({"text": prompt})

# تحويل النص إلى صوت
@app.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text", "")
    audio = generate(
        text=text,
        voice=Voice(
            voice_id="EXAVITQu4vr4xnSDxMaL",  # Hala
            settings=VoiceSettings(stability=0.45, similarity_boost=0.85)
        )
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        f.write(audio)
        f.flush()
        return send_file(f.name, mimetype="audio/mpeg")

# استقبال تسجيل المستخدم وتحليله
@app.route("/transcribe", methods=["POST"])
def handle_transcription():
    audio_data = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        audio_data.save(f.name)
        user_input = transcribe_audio(f.name)
        rephrased = rephrase_text(user_input)
        intent = detect_intent(user_input)

    field = user_session["current_field"]

    if intent == "approve":
        user_session["fields"][field] = rephrased
        next_field = get_next_prompt(field)
        if next_field:
            user_session["current_field"] = next_field
            return jsonify({"next_prompt": field_prompts[next_field]})
        else:
            return jsonify({"done": True})
    elif intent == "redo":
        return jsonify({"next_prompt": field_prompts[field]})
    elif intent == "append":
        user_session["fields"][field] += " " + rephrased
        return jsonify({"next_prompt": f"📌 تم الإضافة. {field_prompts[field]}"})
    elif intent == "correction":
        corrected_field = detect_intent(user_input, return_field=True)
        if corrected_field and corrected_field in user_session["fields"]:
            user_session["current_field"] = corrected_field
            return jsonify({"next_prompt": field_prompts[corrected_field]})
    else:
        return jsonify({"next_prompt": f"هل تقصد: {rephrased}؟ قل نعم أو لا."})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
