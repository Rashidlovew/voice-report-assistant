import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import Voice, VoiceSettings, set_api_key, generate
from docxtpl import DocxTemplate
import smtplib
from email.message import EmailMessage
from pydub import AudioSegment

# ✅ التحقق من نسخة openai
import openai
print("✅ OpenAI version:", openai.__version__)

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

field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]

field_prompts = {
    "Date": "📅 ما هو تاريخ الواقعة؟",
    "Briefing": "📝 أخبرني عن موجز الواقعة.",
    "LocationObservations": "👁️ ماذا لاحظت عند معاينة موقع الحادث؟",
    "Examination": "🔬 ما نتيجة الفحص الفني؟",
    "Outcomes": "📌 ما هي النتائج بعد الفحص؟",
    "TechincalOpinion": "🧠 ما هو رأيك الفني؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

@app.route("/")
def home():
    return "🎙️ Voice Report Assistant is running."

@app.route("/start", methods=["GET"])
def start_session():
    user_session["current_field"] = "Date"
    user_session["fields"] = {}
    return jsonify({
        "message": "مرحباً بك في مساعد إنشاء التقارير الخاص بقسم الهندسة الجنائية.",
        "nextField": "Date",
        "prompt": field_prompts["Date"]
    })

@app.route("/upload", methods=["POST"])
def upload_audio():
    data = request.json
    audio_base64 = data.get("audio")
    if not audio_base64:
        return jsonify({"error": "No audio provided"}), 400

    # حفظ الملف الصوتي مؤقتاً
    audio_data = base64.b64decode(audio_base64.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_data)
        input_path = f.name

    # تحويله إلى wav
    wav_path = input_path.replace(".webm", ".wav")
    AudioSegment.from_file(input_path).export(wav_path, format="wav")

    # إرسال إلى Whisper
    with open(wav_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            response_format="text",
            language="ar"
        )

    # إعادة الصياغة
    rephrased = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "أعد صياغة هذا الإدخال بأسلوب مهني لتقرير فحص هندسي جنائي."},
            {"role": "user", "content": transcript}
        ]
    ).choices[0].message.content.strip()

    # حفظ الرد
    current = user_session["current_field"]
    user_session["fields"][current] = rephrased

    # الانتقال للسؤال التالي
    next_field = get_next_field(current)
    if next_field:
        user_session["current_field"] = next_field
        return jsonify({
            "transcript": transcript,
            "rephrased": rephrased,
            "nextField": next_field,
            "prompt": field_prompts[next_field]
        })
    else:
        # اكتملت جميع الحقول
        return jsonify({
            "transcript": transcript,
            "rephrased": rephrased,
            "nextField": None,
            "prompt": "✅ تم استلام جميع البيانات. جاري إنشاء التقرير...",
            "done": True
        })

def get_next_field(current):
    i = field_order.index(current)
    if i + 1 < len(field_order):
        return field_order[i + 1]
    return None

@app.route("/stream-audio", methods=["POST"])
def stream_audio():
    data = request.json
    message = data.get("message", "مرحباً")
    audio_stream = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",  # صوت أنثوي رسمي عربي
        input=message
    )
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    for chunk in audio_stream.iter_bytes():
        temp.write(chunk)
    temp.close()
    return send_file(temp.name, mimetype="audio/mpeg")

@app.route("/generate-report", methods=["GET"])
def generate_report():
    doc = DocxTemplate("police_report_template.docx")
    context = {field: user_session["fields"].get(field, "") for field in field_order}
    doc.render(context)

    report_path = "generated_report.docx"
    doc.save(report_path)

    send_email(report_path)
    return send_file(report_path, as_attachment=True)

def send_email(attachment_path):
    email_user = os.getenv("EMAIL_USERNAME")
    email_pass = os.getenv("EMAIL_PASSWORD")
    recipient = "frnreports@gmail.com"

    msg = EmailMessage()
    msg["Subject"] = "📄 التقرير الفني"
    msg["From"] = email_user
    msg["To"] = recipient
    msg.set_content("يرجى مراجعة التقرير الفني المرفق 🔍.")

    with open(attachment_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(attachment_path)
        msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(email_user, email_pass)
        smtp.send_message(msg)

# ✅ تأكد من تشغيل السيرفر على Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
