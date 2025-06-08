import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file, Response, render_template
from flask_cors import CORS
from docx import Document
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
import openai

# === Load environment variables ===
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "frnreports@gmail.com")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

openai.api_key = OPENAI_API_KEY

app = Flask(__name__, static_folder="static", template_folder="templates")
CORS(app)

report_fields = [
    "Date",
    "Briefing",
    "LocationObservations",
    "Examination",
    "Outcomes",
    "TechincalOpinion"
]

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

user_sessions = {}

@app.route("/submitAudio", methods=["POST"])
def handle_audio():
    data = request.json
    base64_audio = data["audio"].split(",")[-1]
    audio_data = base64.b64decode(base64_audio)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_data)
        temp_filename = f.name

    with open(temp_filename, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=("audio.webm", audio_file, "audio/webm"),
            response_format="text",
            language="ar"
        )

    user_id = "default"
    session = user_sessions.setdefault(user_id, {"step": 0, "data": {}})
    step = session["step"]

    if step >= len(report_fields):
        return jsonify({"response": "تم الانتهاء من جميع المدخلات.", "transcript": transcript})

    field = report_fields[step]
    session["data"][field] = transcript
    session["step"] += 1

    if session["step"] < len(report_fields):
        next_prompt = field_prompts[report_fields[session["step"]]]
    else:
        next_prompt = "📄 يتم الآن تجهيز التقرير النهائي..."

    if session["step"] == len(report_fields):
        file_path = generate_report(user_id)
        send_email_with_attachment(file_path)
        response = "✅ تم إرسال التقرير عبر البريد الإلكتروني. شكراً لك!"
    else:
        response = next_prompt

    return jsonify({"transcript": transcript, "response": response})


@app.route("/analyze-intent", methods=["POST"])
def analyze_intent():
    data = request.get_json()
    message = data.get("message", "")

    prompt = f"""
المستخدم قال: "{message}"

حدد نيته بناءً على الجملة:
- إذا كان يوافق على الاستمرار، أجب فقط: approve
- إذا كان يريد إعادة الإدخال، أجب فقط: redo
- إذا كان يريد بدء من جديد، أجب فقط: restart
- إذا كان يريد تعديل حقل معين، أجب بصيغة: fieldCorrection:FIELD_KEY

FIELD_KEY يجب أن يكون أحد هذه: Date, Briefing, LocationObservations, Examination, Outcomes, TechincalOpinion
"""

    response = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    reply = response.choices[0].message.content.strip()

    if reply.startswith("fieldCorrection:"):
        field_key = reply.split(":")[1]
        return jsonify({"intent": "fieldCorrection", "field": field_key})
    elif reply == "redo":
        return jsonify({"intent": "redo"})
    elif reply == "restart":
        return jsonify({"intent": "restart"})
    else:
        return jsonify({"intent": "approve"})


def generate_report(user_id):
    session = user_sessions[user_id]
    data = session["data"]

    doc = Document("police_report_template.docx")
    for p in doc.paragraphs:
        for key in report_fields:
            if f"{{{{{key}}}}}" in p.text:
                inline = p.runs
                for i in range(len(inline)):
                    if f"{{{{{key}}}}}" in inline[i].text:
                        inline[i].text = inline[i].text.replace(f"{{{{{key}}}}}", data.get(key, ""))

    output_path = f"report_{user_id}.docx"
    doc.save(output_path)
    return output_path


def send_email_with_attachment(file_path):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg["Subject"] = "📄 Police Report Submission"

    body = MIMEText("Attached is the completed police report.", "plain")
    msg.attach(body)

    with open(file_path, "rb") as f:
        part = MIMEApplication(f.read(), Name=os.path.basename(file_path))
        part["Content-Disposition"] = f'attachment; filename="{os.path.basename(file_path)}"'
        msg.attach(part)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)


@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "مرحباً! كيف يمكنني مساعدتك؟")
    response = openai.audio.speech.create(
        model="tts-1",
        voice="nova",
        input=text
    )

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(response.content)
    temp_file.flush()

    return send_file(temp_file.name, mimetype="audio/mpeg")


@app.route("/")
def index():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
