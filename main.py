from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import openai
import base64
import io
import tempfile
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import datetime
from openai import OpenAI
import smtplib
from email.message import EmailMessage

# === Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

# === Report Fields ===
field_order = [
    "Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"
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

sessions = {}

# === Routes ===

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/clientIP")
def get_ip():
    return jsonify({"ip": request.remote_addr})

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    if not text:
        return "No text", 400

    # ✅ FIXED: Removed language="ar"
    speech = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text
    )
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    speech.stream_to_file(temp_file.name)
    return send_file(temp_file.name, mimetype="audio/mpeg")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    user_id = request.remote_addr
    if user_id not in sessions:
        sessions[user_id] = {"step": 0, "data": {}}

    audio_data = request.json.get("audio")
    if not audio_data:
        return jsonify({"error": "No audio data provided"}), 400

    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.webm"  # Important for OpenAI to recognize format

    transcript = transcribe_audio(audio_file)
    current_field = field_order[sessions[user_id]["step"]]
    interpretation = analyze_intent(transcript)

    action = "next"
    if interpretation == "redo":
        response = f"↩️ يرجى إعادة إرسال {field_names_ar[current_field]}"
        action = "redo"
    elif interpretation == "restart":
        sessions[user_id] = {"step": 0, "data": {}}
        current_field = field_order[0]
        response = field_prompts[current_field]
        action = "restart"
    elif interpretation.startswith("field:"):
        target_field = interpretation.split(":")[1]
        if target_field in field_order:
            sessions[user_id]["step"] = field_order.index(target_field)
            response = f"🎙️ حسنًا، أعد إرسال {field_names_ar[target_field]}"
            action = "redo"
        else:
            response = "❌ لم أفهم الطلب، حاول مرة أخرى."
            action = "unknown"
    else:
        sessions[user_id]["data"][current_field] = transcript
        sessions[user_id]["step"] += 1
        if sessions[user_id]["step"] >= len(field_order):
            file_path = generate_report(sessions[user_id]["data"])
            send_email("frnreports@gmail.com", file_path)
            del sessions[user_id]
            response = "📄 تم إعداد التقرير وإرساله بنجاح عبر البريد الإلكتروني. شكرًا لتعاونك."
            action = "done"
        else:
            next_field = field_order[sessions[user_id]["step"]]
            response = field_prompts[next_field]

    return jsonify({
        "transcript": transcript,
        "response": response,
        "action": action
    })

# === Helpers ===

def transcribe_audio(audio_file):
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file,
        response_format="text",
        language="ar"
    )
    return result.strip()

def analyze_intent(text):
    prompt = f"""
حلل نية المستخدم بناءً على الجملة التالية:
"{text}"
هل يريد (الموافقة - الإعادة - إعادة من البداية - تصحيح حقل معين)؟ 
أجب فقط بإحدى: approve, redo, restart, field:<field_name_in_english>, أو unknown.
"""
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    intent = res.choices[0].message.content.strip()
    return intent

def generate_report(data):
    doc = Document("police_report_template.docx")
    for para in doc.paragraphs:
        for key, value in data.items():
            if f"{{{{{key}}}}}" in para.text:
                para.text = para.text.replace(f"{{{{{key}}}}}", value)
                para.rtl = True
                para.paragraph_format.alignment = 2  # Right align
                run = para.runs[0]
                run.font.name = 'Dubai'
                run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Dubai')
                run.font.size = Pt(13)

    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_path = f"/tmp/report_{now}.docx"
    doc.save(file_path)
    return file_path

def send_email(to, file_path):
    msg = EmailMessage()
    msg["Subject"] = "📄 التقرير الفني بعد الفحص"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to
    msg.set_content("تم إعداد التقرير الفني بناءً على المعلومات المرسلة.")

    with open(file_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(file_path)
        msg.add_attachment(file_data, maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

# === Run App ===
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
