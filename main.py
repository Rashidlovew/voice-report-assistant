import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, set_api_key, Voice, VoiceSettings

print("✅ OpenAI version:", OpenAI.__module__)

app = Flask(__name__)
CORS(app)

# إعداد مفاتيح API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# بيانات المستخدم
user_session = {
    "current_field": "Date",
    "fields": {},
}

# الحقول والتسميات بالعربية
field_prompts = {
    "Date": "🎙️ حدثني عن تاريخ الواقعة.",
    "Briefing": "🎙️ ما هو موجز الواقعة؟",
    "LocationObservations": "🎙️ ماذا لاحظت أثناء معاينة الموقع؟",
    "Examination": "🎙️ ما هي نتيجة الفحص الفني؟",
    "Outcomes": "🎙️ ما هي النتيجة النهائية بعد الفحص؟",
    "TechincalOpinion": "🎙️ ما هو رأيك الفني؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

# تحويل النص إلى صوت باستخدام ElevenLabs بصوت Rachel
def text_to_speech_arabic(text):
    audio = generate(
        text=text,
        voice=Voice(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
            settings=VoiceSettings(stability=0.5, similarity_boost=0.8)
        )
    )
    temp_path = tempfile.mktemp(suffix=".mp3")
    with open(temp_path, "wb") as f:
        f.write(audio)
    return temp_path

# تحويل الصوت إلى نص باستخدام Whisper API
def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            response_format="text"
        )
    return transcript

# إعادة صياغة النص بشكل احترافي
def rephrase_text_arabic(text):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أنت مساعد ذكي تعيد صياغة إجابات المستخدم بشكل مهني لاستخدامها في تقرير شرطة."},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()

# استقبال التسجيل الصوتي من الواجهة
@app.route("/transcribe", methods=["POST"])
def handle_transcription():
    audio_data = request.json["audio"]
    field = request.json.get("field")

    if not audio_data or not field:
        return jsonify({"error": "Invalid data"}), 400

    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(audio_bytes)
        temp_audio_path = temp_audio.name

    try:
        text = transcribe_audio(temp_audio_path)
        cleaned = rephrase_text_arabic(text)
        user_session["fields"][field] = cleaned
        return jsonify({"text": cleaned})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# توليد الصوت من النص
@app.route("/speak", methods=["POST"])
def handle_speak():
    data = request.json
    text = data.get("text", "")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    try:
        audio_path = text_to_speech_arabic(text)
        return send_file(audio_path, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# الحصول على الحقل التالي
@app.route("/next", methods=["GET"])
def get_next_prompt():
    fields = list(field_prompts.keys())
    current = user_session["current_field"]
    try:
        idx = fields.index(current)
        if idx + 1 < len(fields):
            next_field = fields[idx + 1]
            user_session["current_field"] = next_field
            return jsonify({"field": next_field, "prompt": field_prompts[next_field]})
        else:
            return jsonify({"done": True})
    except ValueError:
        return jsonify({"error": "Invalid field"}), 400

# الحصول على القيم المدخلة
@app.route("/inputs", methods=["GET"])
def get_inputs():
    return jsonify(user_session["fields"])

# إعادة تعيين الجلسة
@app.route("/reset", methods=["POST"])
def reset_session():
    user_session["current_field"] = "Date"
    user_session["fields"] = {}
    return jsonify({"message": "تمت إعادة ضبط الجلسة."})

# ====== إعداد المنفذ لـ Render ======
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
