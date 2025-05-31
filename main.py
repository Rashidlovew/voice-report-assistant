import os
import tempfile
import json
from flask import Flask, request, jsonify, send_file, render_template
from openai import OpenAI
from docxtpl import DocxTemplate
from docx.shared import Pt
from docx.oxml.ns import qn
from pydub import AudioSegment
from email.message import EmailMessage
import smtplib
import requests

# Configuration
OPENAI_KEY = os.environ["OPENAI_KEY"]
ELEVENLABS_KEY = os.environ["ELEVENLABS_KEY"]
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER", "frnreports@gmail.com")
TEMPLATE_FILE = "police_report_template.docx"

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_KEY)

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

field_order = list(field_names_ar.keys())
session_data = {}

def format_paragraph(p):
    if p.runs:
        run = p.runs[0]
        run.font.name = 'Dubai'
        run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Dubai')
        run.font.size = Pt(13)

def format_report_doc(doc):
    for para in doc.paragraphs:
        format_paragraph(para)

def generate_report(data, file_path):
    tpl = DocxTemplate(TEMPLATE_FILE)
    tpl.render(data)
    format_report_doc(tpl.docx)
    tpl.save(file_path)

def transcribe_audio(file_path):
    audio = AudioSegment.from_file(file_path)
    wav_path = tempfile.mktemp(suffix=".wav")
    audio.export(wav_path, format="wav")
    with open(wav_path, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            file=audio_file,
            model="whisper-1",
            language="ar"
        )
    return transcript.text

def enhance_with_gpt(field_name, user_input, edit_instruction=None):
    if edit_instruction:
        prompt = (
            f"لدي النص التالي المرتبط بـ {field_names_ar.get(field_name)}:\n\n"
            f"{user_input}\n\n"
            f"يرجى تنفيذ التعديلات التالية فقط دون كتابة التعليمات نفسها:\n"
            f"{edit_instruction}\n\n"
            f"🔁 الناتج يجب أن يكون بصيغة رسمية وعربية فصحى، يحافظ على المعنى الأصلي، "
            f"ولا يتضمن الكلمات مثل 'أضف' أو 'احذف' أو 'استبدل'."
        )
    elif field_name == "Date":
        prompt = (
            f"أعد كتابة التاريخ الوارد بصيغة رسمية بالتنسيق التالي فقط (مثال: 20/مايو/2025)، "
            f"بدون إضافة أي شيء آخر. النص:\n\n{user_input}"
        )
    else:
        prompt = (
            f"أعد صياغة النص التالي ({field_names_ar.get(field_name)}) بلغة عربية فصحى ورسمية، "
            f"بدون تغيير المعنى وبدون أي إضافات أو مشاعر:\n\n{user_input}"
        )
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def speak_text(text):
    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/jN1a8k1Wv56Yf63YzCYr/stream",
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json"
        },
        json={
            "text": text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
        }
    )
    return response.content

def send_email(subject, body, to, attachment_path):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL_SENDER
    msg["To"] = to
    msg.set_content(body)
    with open(attachment_path, "rb") as f:
        msg.add_attachment(
            f.read(), maintype="application",
            subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=os.path.basename(attachment_path)
        )
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/voice", methods=["POST"])
def handle_voice():
    field = request.form["field"]
    audio_file = request.files["audio"]
    tmp_path = tempfile.mktemp(suffix=".webm")
    audio_file.save(tmp_path)

    try:
        raw_text = transcribe_audio(tmp_path)
        rephrased = enhance_with_gpt(field, raw_text)
        audio_reply = speak_text(rephrased)
        session_data[field] = rephrased

        return jsonify({
            "text": rephrased,
            "audio": f"/audio/{field}.mp3"
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/reply", methods=["POST"])
def handle_reply():
    field = request.json["field"]
    action = request.json["action"]
    if action == "redo":
        session_data.pop(field, None)
        return jsonify({"status": "redo"})
    elif action.startswith("edit:"):
        original = session_data.get(field, "")
        edit_instruction = action.replace("edit:", "").strip()
        new_text = enhance_with_gpt(field, original, edit_instruction)
        session_data[field] = new_text
        audio_reply = speak_text(new_text)
        return jsonify({"text": new_text})
    elif action == "approve":
        return jsonify({"status": "approved"})
    return jsonify({"error": "Invalid action"}), 400

@app.route("/generate", methods=["POST"])
def generate_and_send():
    if not all(f in session_data for f in field_order):
        return jsonify({"error": "Missing fields"}), 400

    filename = "police_report.docx"
    generate_report(session_data, filename)
    send_email("📄 تقرير فحص", "تم إعداد التقرير وإرفاقه في البريد.", EMAIL_RECEIVER, filename)
    return send_file(filename, as_attachment=True)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
