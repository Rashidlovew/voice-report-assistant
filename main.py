import os
import io
import base64
import smtplib
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from email.message import EmailMessage
from docx import Document
from docx.shared import Pt
from openai import OpenAI
from datetime import datetime

app = Flask(__name__)
CORS(app)

openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

DEPARTMENT_EMAIL = "frnreports@gmail.com"
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

# Arabic field definitions
field_prompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و إجراء الفحوص الفنية اللازمة تبين ما يلي:.",
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
field_order = list(field_prompts.keys())

sessions = {}

@app.route("/")
def index():
    return "Voice Report Assistant is running."

@app.route("/clientIP")
def client_ip():
    return jsonify({"ip": request.remote_addr})

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    if not text:
        return "Missing text", 400
    speech_response = openai_client.audio.speech.create(
        model="tts-1",
        voice="shimmer",  # Arabic-compatible OpenAI voice
        input=text
    )
    audio_data = io.BytesIO(speech_response.read())
    return send_file(audio_data, mimetype="audio/mpeg")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_base64 = data.get("audio", "").split(",")[1]
    audio_bytes = base64.b64decode(audio_base64)

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(audio_bytes)
        temp_filename = temp_file.name

    transcript = transcribe_audio(temp_filename)
    os.remove(temp_filename)

    user_id = "default_user"
    session = sessions.setdefault(user_id, {"step": 0, "data": {}})
    step = session["step"]

    current_field = field_order[step] if step < len(field_order) else None
    session["last_transcript"] = transcript

    # Analyze intent with GPT
    intent = analyze_intent(transcript)

    if intent == "redo":
        reply = f"↩️ يرجى إعادة إرسال {field_names_ar[current_field]}"
    elif intent == "restart":
        session["step"] = 0
        session["data"] = {}
        reply = "🔄 تم البدء من جديد، " + field_prompts[field_order[0]]
    elif intent == "approve":
        session["data"][current_field] = transcript
        session["step"] += 1
        if session["step"] < len(field_order):
            next_field = field_order[session["step"]]
            reply = f"✅ تم تسجيل {field_names_ar[current_field]}.\n{field_prompts[next_field]}"
        else:
            filename = generate_report(session["data"])
            send_email_with_attachment(filename, DEPARTMENT_EMAIL)
            reply = "📄 تم إعداد التقرير بنجاح وإرساله بالبريد الإلكتروني. شكراً لك!"
    elif intent.startswith("field:"):
        field_key = intent.split(":")[1]
        session["step"] = field_order.index(field_key)
        reply = f"↩️ يرجى إعادة إرسال {field_names_ar[field_key]}"
    else:
        reply = f"هل تقصد \"{transcript}\" كـ {field_names_ar[current_field]}؟"

    return jsonify({
        "transcript": transcript,
        "response": reply
    })

def transcribe_audio(file_path):
    with open(file_path, "rb") as audio_file:
        transcript = openai_client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            response_format="text"
        )
        return transcript.strip()

def analyze_intent(transcript):
    prompt = f"""
    Analyze the following user message in Arabic and return the user's intent as one of:
    - approve
    - redo
    - restart
    - field:<field_key>

    User said: "{transcript}"
    Return ONLY one of the above, no explanation.
    """
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "system", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

def generate_report(data):
    template = Document("police_report_template.docx")
    for para in template.paragraphs:
        for key in field_order:
            placeholder = f"<<{key}>>"
            if placeholder in para.text:
                para.text = para.text.replace(placeholder, data.get(key, ""))
                for run in para.runs:
                    run.font.name = "Dubai"
                    run.font.size = Pt(13)
                para.paragraph_format.right_to_left = True
                para.alignment = 2
    filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.docx"
    template.save(filename)
    return filename

def send_email_with_attachment(file_path, recipient):
    msg = EmailMessage()
    msg["Subject"] = "📄 التقرير الفني جاهز"
    msg["From"] = EMAIL_SENDER
    msg["To"] = recipient
    msg.set_content("تم إرفاق التقرير الفني في هذا البريد. شكراً لتعاونك.")

    with open(file_path, "rb") as f:
        file_data = f.read()
        msg.add_attachment(file_data, maintype="application",
                           subtype="vnd.openxmlformats-officedocument.wordprocessingml.document",
                           filename=os.path.basename(file_path))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_SENDER, EMAIL_PASSWORD)
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
