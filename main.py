import os
import tempfile
import json
from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from docxtpl import DocxTemplate
from docx.shared import Pt
from docx.oxml.ns import qn
from pydub import AudioSegment
from email.message import EmailMessage
import smtplib
import requests

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

current_field_index = 0
user_inputs = {}

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
        "https://api.elevenlabs.io/v1/text-to-speech/jN1a8k1Wv56Yf63YzCYr",
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        },
        json={
            "text": text,
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
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

def detect_action(text):
    t = text.strip().replace("،", "").replace(".", "")
    if t in ["نعم", "اعتمد", "تمام"]:
        return "approve"
    if t in ["لا", "إعادة", "أعد", "كرر"]:
        return "redo"
    if t.startswith("أضف") or t.startswith("غير") or t.startswith("استبدل"):
        return f"edit:{t}"
    return "input"

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start_session():
    global current_field_index, user_inputs
    current_field_index = 0
    user_inputs = {}
    return "ok"

@app.route("/fieldPrompt")
def field_prompt():
    if current_field_index >= len(field_order):
        filename = "police_report.docx"
        generate_report(user_inputs, filename)
        send_email("📄 تقرير فحص", "تم إعداد التقرير وإرفاقه في البريد.", EMAIL_RECEIVER, filename)
        return jsonify({"done": True})

    field = field_order[current_field_index]
    prompt = f"🎙️ {field_names_ar[field]}، الرجاء التحدث."
    audio = speak_text(prompt)
    return jsonify({"prompt": prompt, "audio": list(audio)})

@app.route("/listen", methods=["POST"])
def listen_reply():
    global current_field_index
    field = field_order[current_field_index]
    audio_file = request.files["audio"]
    tmp_path = tempfile.mktemp(suffix=".webm")
    audio_file.save(tmp_path)

    text = transcribe_audio(tmp_path).strip()
    action = detect_action(text)

    if action == "approve":
        current_field_index += 1
        return jsonify({"action": "تم الاعتماد", "audio": list(speak_text("تم الاعتماد"))})

    elif action == "redo":
        return jsonify({"action": "يرجى إعادة الإرسال", "audio": list(speak_text("يرجى إعادة الإرسال"))})

    elif action.startswith("edit:"):
        edit_instr = action.replace("edit:", "")
        revised = enhance_with_gpt(field, user_inputs[field], edit_instr)
        user_inputs[field] = revised
        return jsonify({"action": "تم التعديل", "text": revised, "audio": list(speak_text("تم التعديل"))})

    elif action == "input":
        user_inputs[field] = text
        preview = enhance_with_gpt(field, text)
        user_inputs[field] = preview
        return jsonify({
            "action": "هل ترغب بالاعتماد؟",
            "text": preview,
            "audio": list(speak_text(f"{preview}. هل ترغب بالاعتماد؟"))
        })

    return jsonify({"error": "Unrecognized response."}), 400

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
