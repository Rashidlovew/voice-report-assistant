import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from openai import OpenAI
from docxtpl import DocxTemplate
from datetime import datetime
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)

openai = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

TTS_VOICE = "nova"

field_prompts = {
    "Date": "أرسل التاريخ من فضلك.",
    "Briefing": "أرسل موجز الواقعة.",
    "LocationObservations": "أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "أرسل النتيجة حيث أنه بعد المعاينة و إجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "أرسل الرأي الفني."
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

sessions = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    response = openai.audio.speech.create(
        model="tts-1",
        voice=TTS_VOICE,
        input=text
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    response.stream_to_file(temp_file.name)
    return send_file(temp_file.name, mimetype="audio/mpeg")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_data = data["audio"].split(",")[1]
    audio_bytes = base64.b64decode(audio_data)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_bytes)
        temp_path = f.name

    audio_file = open(temp_path, "rb")
    transcript = openai.audio.transcriptions.create(model="whisper-1", file=audio_file, language="ar").text

    session_id = "default"
    current_field = get_current_field(session_id)
    rephrased = rephrase_text(transcript, current_field)

    sessions.setdefault(session_id, {})[current_field] = rephrased
    return jsonify({"transcript": transcript, "response": rephrased})

@app.route("/analyze-intent", methods=["POST"])
def analyze_intent():
    message = request.get_json()["message"]
    prompt = f'''
أنت مساعد ذكي. استخرج نية المستخدم من الجملة التالية:

"{message}"

النيات المحتملة:
- الموافقة
- إعادة
- إضافة
- تصحيح: متبوعة باسم الحقل (مثل تصحيح التاريخ)
- إعادة البدء

أجب فقط بواحدة من الكلمات التالية: "موافقة", "إعادة", "إضافة", "إعادة البدء", أو "تصحيح: <اسم الحقل>"
'''
    result = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content.strip()

    if "موافقة" in result:
        return jsonify({"intent": "approve"})
    elif "إعادة البدء" in result:
        sessions["default"] = {}
        return jsonify({"intent": "restart"})
    elif "إعادة" in result:
        return jsonify({"intent": "redo"})
    elif "إضافة" in result:
        return jsonify({"intent": "append"})
    elif "تصحيح" in result:
        field = result.split(":")[-1].strip()
        return jsonify({"intent": "fieldCorrection", "field": field})
    else:
        return jsonify({"intent": "unknown"})

def get_current_field(session_id):
    data = sessions.get(session_id, {})
    for field in field_prompts:
        if field not in data:
            return field
    return None

def rephrase_text(input_text, field):
    if field == "Date":
        prompt = f"استخرج التاريخ فقط من الجملة التالية دون أي كلمات إضافية:
{input_text}"
    else:
        prompt = f"أعد صياغة النص التالي بشكل رسمي ومهني:
{input_text}"
    result = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return result.choices[0].message.content.strip()

@app.route("/send-report", methods=["POST"])
def send_report():
    session_id = "default"
    inputs = sessions.get(session_id, {})
    if not inputs or len(inputs) < len(field_prompts):
        return jsonify({"status": "error", "message": "لم يتم استكمال جميع الحقول."})

    doc = DocxTemplate("police_report_template.docx")
    doc.render(inputs)
    output_path = f"/tmp/report_{datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
    doc.save(output_path)

    send_email_with_attachment("your@email.com", "تقرير الفحص", "مرفق تقرير الشرطة", output_path)
    return jsonify({"status": "done", "path": output_path})

def send_email_with_attachment(to_email, subject, body, file_path):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = "report@assistant.com"
    msg["To"] = to_email
    msg.set_content(body)

    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename="report.docx")

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASS"))
        server.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
