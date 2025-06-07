import os
import tempfile
import base64
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, save, set_api_key, Voice, VoiceSettings
from docxtpl import DocxTemplate
from datetime import datetime
import speech_recognition as sr

app = Flask(__name__)
CORS(app)

# إعداد المفاتيح
openai_api_key = os.getenv("OPENAI_API_KEY")
elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
client = OpenAI(api_key=openai_api_key)
set_api_key(elevenlabs_api_key)

# إعداد الصوت - Hala صوت عربي
voice_id = "EXAVITQu4vr4xnSDxMaL"

# إعدادات المشروع
report_fields = [
    "Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"
]

field_prompts = {
    "Date": "🎙️ أخبرني بتاريخ الواقعة.",
    "Briefing": "🎙️ ما هو موجز الواقعة؟",
    "LocationObservations": "🎙️ ماذا لاحظت عند معاينة موقع الحادث؟",
    "Examination": "🎙️ ما نتائج الفحص الفني؟",
    "Outcomes": "🎙️ ما هي النتائج التي توصلت إليها؟",
    "TechincalOpinion": "🎙️ ما هو الرأي الفني النهائي؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

user_session = {
    "current_field_index": 0,
    "fields": {}
}

def speak_text(text):
    audio_stream = generate(
        text=text,
        voice=Voice(voice_id=voice_id, settings=VoiceSettings(stability=0.4, similarity_boost=0.75)),
        model="eleven_multilingual_v2",
        stream=True
    )
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
        save(audio_stream, f.name)
        return f.name

@app.route("/", methods=["GET"])
def greet():
    greeting_text = "مرحباً بك. هذا هو مساعد التقارير الخاص بقسم الهندسة الجنائية. أنا هنا لمساعدتك في كتابة تقرير رسمي خطوة بخطوة."
    audio_path = speak_text(greeting_text)
    return send_file(audio_path, mimetype="audio/mpeg")

@app.route("/next", methods=["GET"])
def next_prompt():
    idx = user_session["current_field_index"]
    if idx >= len(report_fields):
        return jsonify({"done": True})
    current_field = report_fields[idx]
    prompt = field_prompts[current_field]
    audio_path = speak_text(prompt)
    return send_file(audio_path, mimetype="audio/mpeg")

@app.route("/speak", methods=["POST"])
def receive_input():
    data = request.get_json()
    user_text = data.get("text", "")

    idx = user_session["current_field_index"]
    current_field = report_fields[idx]

    # Rephrase input using GPT
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": f"صغ هذا النص بأسلوب تقرير شرطة رسمي: {user_text}"}],
    )
    rephrased = response.choices[0].message.content.strip()
    user_session["fields"][current_field] = rephrased
    user_session["current_field_index"] += 1

    # الرد الصوتي
    if user_session["current_field_index"] < len(report_fields):
        next_field = report_fields[user_session["current_field_index"]]
        next_prompt = field_prompts[next_field]
        audio_path = speak_text(f"تم تسجيل {field_names_ar[current_field]}. {next_prompt}")
    else:
        audio_path = speak_text("تم تسجيل جميع الحقول. سيتم الآن إرسال التقرير عبر البريد الإلكتروني.")
        generate_report_and_send()

    return send_file(audio_path, mimetype="audio/mpeg")

def generate_report_and_send():
    doc = DocxTemplate("police_report_template.docx")
    doc.render(user_session["fields"])
    output_path = f"/tmp/final_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc.save(output_path)

    # يمكن لاحقاً استخدام خدمة إرسال بريد مثل SendGrid أو SMTP هنا
    print(f"📄 Report ready at: {output_path}")

@app.route("/reset", methods=["POST"])
def reset_session():
    user_session["current_field_index"] = 0
    user_session["fields"] = {}
    return jsonify({"status": "reset"})


if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
