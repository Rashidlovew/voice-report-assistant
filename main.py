from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
import os, base64, io, tempfile, datetime
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
import smtplib
from email.message import EmailMessage
from openai import OpenAI

# === Config ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_USER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASS")
client = OpenAI(api_key=OPENAI_API_KEY)

app = Flask(__name__)
CORS(app)

field_order = [
    "Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"
]

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
    speech = client.audio.speech.create(
        model="tts-1",
        voice="shimmer",
        input=text
    )
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    speech.stream_to_file(tmp.name)
    return send_file(tmp.name, mimetype="audio/mpeg")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    user_id = request.remote_addr
    if user_id not in sessions:
        sessions[user_id] = {"step": 0, "data": {}, "last_field": None}

    data = request.json
    audio_data = data.get("audio")

    if not audio_data:
        field = field_order[sessions[user_id]["step"]]
        prompt = generate_prompt(field)
        return jsonify({"response": prompt, "action": "prompt"})

    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.webm"
    transcript = transcribe_audio(audio_file)

    step = sessions[user_id]["step"]
    if step >= len(field_order):
        return jsonify({
            "transcript": transcript,
            "response": "📄 جميع الحقول تم جمعها بالفعل.",
            "action": "done"
        })

    field = field_order[step]
    intent = detect_intent(transcript)

    if intent == "redo":
        return jsonify({
            "transcript": transcript,
            "response": f"🔁 حسنًا، أعد {field_names_ar[field]} من فضلك.",
            "action": "redo"
        })

    elif intent == "restart":
        sessions[user_id] = {"step": 0, "data": {}, "last_field": None}
        prompt = generate_prompt("Date")
        return jsonify({
            "transcript": transcript,
            "response": "🔄 تم إعادة البدء. " + prompt,
            "action": "restart"
        })

    elif intent.startswith("field:"):
        target = intent.split(":")[1]
        if target in field_order:
            sessions[user_id]["step"] = field_order.index(target)
            prompt = generate_prompt(target)
            return jsonify({
                "transcript": transcript,
                "response": f"↩️ نعود إلى {field_names_ar[target]}.\n" + prompt,
                "action": "jump"
            })

    # Append to previous value if exists
    prev_text = sessions[user_id]["data"].get(field, "")
    sessions[user_id]["data"][field] = prev_text + " " + transcript if prev_text else transcript

    # ✅ تأكيد صياغي + الانتقال خطوة واحدة فقط إذا لم تكن مكررة
    sessions[user_id]["last_field"] = field
    confirm = confirm_reply(field, sessions[user_id]["data"][field])
    sessions[user_id]["step"] += 1

    if sessions[user_id]["step"] >= len(field_order):
        file_path = generate_report(sessions[user_id]["data"])
        send_email("frnreports@gmail.com", file_path)
        del sessions[user_id]
        return jsonify({
            "transcript": transcript,
            "response": confirm + "\n📩 تم إرسال التقرير عبر البريد الإلكتروني. شكرًا لتعاونك.",
            "action": "done"
        })
    else:
        next_field = field_order[sessions[user_id]["step"]]
        prompt = generate_prompt(next_field)
        return jsonify({
            "transcript": transcript,
            "response": confirm + "\n" + prompt,
            "action": "next"
        })

def transcribe_audio(file):
    result = client.audio.transcriptions.create(
        model="whisper-1",
        file=file,
        response_format="text",
        language="ar"
    )
    return result.strip()

def detect_intent(text):
    prompt = f"""
حلل نية المستخدم من العبارة: "{text}"
اختر فقط من:
- approve
- redo
- restart
- field:<FieldName>
- unknown
"""
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()

def generate_prompt(field):
    prompt = f"اكتب جملة رسمية مؤنثة باللغة العربية تطلب من المستخدم تزويدك بـ {field_names_ar[field]}"
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()

def confirm_reply(field, text):
    prompt = f"""
أعد صياغة التالي بأسلوب رسمي مهذب باللغة العربية كمساعد صوتي:
"{text}"
ثم أضف تأكيدًا أنك استلمت {field_names_ar[field]}.
"""
    res = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()

def generate_report(data):
    doc = Document("police_report_template.docx")
    for para in doc.paragraphs:
        for key, val in data.items():
            if f"{{{{{key}}}}}" in para.text:
                para.text = para.text.replace(f"{{{{{key}}}}}", val)
                para.rtl = True
                para.paragraph_format.alignment = 2
                run = para.runs[0]
                run.font.name = "Dubai"
                run._element.rPr.rFonts.set(qn("w:eastAsia"), "Dubai")
                run.font.size = Pt(13)
    path = f"/tmp/report_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    doc.save(path)
    return path

def send_email(to, file_path):
    msg = EmailMessage()
    msg["Subject"] = "📄 التقرير الفني"
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to
    msg.set_content("تم تجهيز التقرير الفني بناءً على البيانات المدخلة.")
    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=os.path.basename(file_path))
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
