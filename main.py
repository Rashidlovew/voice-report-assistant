import os
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import set_api_key, generate

# إعداد Flask
app = Flask(__name__)
CORS(app)

# مفاتيح API
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# الصوت العربي الرسمي من ElevenLabs
voice_id = "EXAVITQu4vr4xnSDxMaL"

# بيانات الجلسة
user_session = {
    "current_field": "Date",
    "fields": {},
}

# تسلسل الحقول
field_order = [
    "Date",
    "Briefing",
    "LocationObservations",
    "Examination",
    "Outcomes",
    "TechincalOpinion"
]

# الرسائل المخصصة
field_prompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

# 🎤 إنشاء صوت من نص
@app.route("/speak", methods=["POST"])
def speak():
    data = request.json
    text = data.get("text", "")
    audio_stream = generate(
        text=text,
        voice=voice_id,
        model="eleven_multilingual_v2",
        stream=True
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        for chunk in audio_stream:
            f.write(chunk)
        temp_path = f.name
    return send_file(temp_path, mimetype="audio/mpeg")

# 🧠 ابدأ التفاعل: ترحيب + أول سؤال
@app.route("/next", methods=["GET"])
def next_prompt():
    current = user_session["current_field"]
    text = field_prompts[current]
    return jsonify({"text": text})

# 📝 استلام الرد الصوتي وتحديث الحالة
@app.route("/reply", methods=["POST"])
def handle_reply():
    data = request.json
    text = data.get("text", "")
    field = user_session["current_field"]
    user_session["fields"][field] = text

    next_index = field_order.index(field) + 1
    if next_index < len(field_order):
        user_session["current_field"] = field_order[next_index]
        next_field = field_order[next_index]
        return jsonify({
            "next": True,
            "field": next_field,
            "text": field_prompts[next_field]
        })
    else:
        return jsonify({
            "next": False,
            "done": True,
            "fields": user_session["fields"]
        })

# 🧪 اختبار الاتصال
@app.route("/", methods=["GET"])
def home():
    return "Voice Assistant is running ✅"

