import os
import tempfile
import base64
import time
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, save, set_api_key
from docxtpl import DocxTemplate

app = Flask(__name__)
CORS(app)

# API keys
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# Voice setup
voice_id = "EXAVITQu4vr4xnSDxMaL"  # Hala

# Session state
user_session = {
    "current_field": "Date",
    "fields": {},
    "history": [],
}

field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]

field_prompts = {
    "Date": "🗓️ ما هو تاريخ الواقعة؟",
    "Briefing": "📌 أخبرني باختصار عن الواقعة.",
    "LocationObservations": "👁️ ماذا لاحظت في موقع الحادث؟",
    "Examination": "🧪 ما نتيجة الفحص الفني؟",
    "Outcomes": "📊 ما النتيجة التي توصلت لها بعد الفحص؟",
    "TechincalOpinion": "🧠 ما هو رأيك الفني النهائي؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}


def speak(text):
    audio = generate(text=text, voice=voice_id, model="eleven_monolingual_v1")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        save(audio, f.name)
        return f.name


def get_next_field():
    for field in field_order:
        if field not in user_session["fields"]:
            return field
    return None


@app.route("/next", methods=["GET"])
def get_next():
    field = get_next_field()
    if field:
        user_session["current_field"] = field
        prompt = field_prompts[field]
        return jsonify({"field": field, "prompt": prompt})
    return jsonify({"done": True})


@app.route("/speak", methods=["POST"])
def handle_speak():
    data = request.json
    text = data.get("text", "").strip()
    field = user_session["current_field"]

    if not text:
        return jsonify({"reply": "لم أسمع شيئاً. هل يمكنك التحدث مجدداً؟"})

    # Step 1: Rephrase input
    response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "أعد صياغة هذا الإدخال ليكون بلغة رسمية مناسبة لتقرير شرطة، مع الحفاظ على المعنى الكامل."},
            {"role": "user", "content": text}
        ],
        model="gpt-4"
    )
    rephrased = response.choices[0].message.content.strip()

    # Step 2: Detect intent
    intent_response = client.chat.completions.create(
        messages=[
            {"role": "system", "content": "حلل نية المستخدم بناءً على هذا الإدخال الصوتي. هل ينوي (تأكيد، إعادة، تعديل، إضافة، الرجوع لحقل سابق)؟ أجب بكلمة واحدة فقط: تأكيد، إعادة، تعديل، إضافة، رجوع."},
            {"role": "user", "content": text}
        ],
        model="gpt-4"
    )
    intent = intent_response.choices[0].message.content.strip()

    if intent == "إعادة":
        prompt = field_prompts[field]
        return jsonify({"reply": prompt, "field": field})

    elif intent == "تعديل":
        return jsonify({"reply": f"يرجى إعادة إرسال {field_names_ar[field]}.", "field": field})

    elif intent == "إضافة":
        user_session["fields"][field] += " " + rephrased
        return jsonify({"reply": "تمت إضافة المعلومة. هل نتابع؟", "field": field})

    elif intent == "رجوع":
        previous_index = field_order.index(field) - 1
        if previous_index >= 0:
            previous_field = field_order[previous_index]
            user_session["current_field"] = previous_field
            return jsonify({"reply": field_prompts[previous_field], "field": previous_field})

    # Default: تأكيد
    user_session["fields"][field] = rephrased
    next_field = get_next_field()
    if next_field:
        user_session["current_field"] = next_field
        reply = f"{field_names_ar[field]} تم تسجيله ✅ الآن {field_prompts[next_field]}"
        return jsonify({"reply": reply, "field": next_field})
    else:
        return jsonify({"reply": "📄 تم استلام جميع البيانات. يتم الآن إنشاء التقرير...", "done": True})


@app.route("/reset", methods=["POST"])
def reset():
    user_session["current_field"] = "Date"
    user_session["fields"] = {}
    user_session["history"] = []
    return jsonify({"reply": "🔄 تم إعادة ضبط الجلسة. لنبدأ من جديد.", "field": "Date"})


@app.route("/audio", methods=["POST"])
def generate_audio():
    data = request.json
    text = data.get("text", "")
    path = speak(text)
    with open(path, "rb") as f:
        audio_data = f.read()
    return audio_data, 200, {'Content-Type': 'audio/mpeg'}

port = int(os.environ.get("PORT", 10000))
app.run(host="0.0.0.0", port=port)
