import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file, render_template
from openai import OpenAI
from docxtpl import DocxTemplate
from pydub import AudioSegment
import smtplib
from email.message import EmailMessage
import re

app = Flask(__name__)
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

session_data = {}
fields = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]
field_prompts = {
    "Date": "يرجى تزويدي بتاريخ الواقعة.",
    "Briefing": "يرجى تزويدي بموجز الواقعة.",
    "LocationObservations": "يرجى تزويدي بمعاينة الموقع.",
    "Examination": "يرجى تزويدي بنتيجة الفحص الفني.",
    "Outcomes": "يرجى تزويدي بالنتيجة.",
    "TechincalOpinion": "يرجى تزويدي بالرأي الفني."
}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_data = data["audio"].split(",")[1]
    audio_bytes = base64.b64decode(audio_data)

    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
        temp_file.write(audio_bytes)
        webm_path = temp_file.name

    wav_path = webm_path.replace(".webm", ".wav")
    AudioSegment.from_file(webm_path).export(wav_path, format="wav")

    transcript = transcribe_audio(wav_path)
    field = fields[len(session_data)]
    if field == "Date":
        extracted = extract_date_from_text(transcript)
    else:
        extracted = transcript

    session_data[field] = extracted

    return jsonify({"transcript": transcript, "response": extracted})

def transcribe_audio(file_path):
    audio_file = open(file_path, "rb")
    transcript = client.audio.transcriptions.create(model="whisper-1", file=audio_file)
    return transcript.text

def extract_date_from_text(text):
    prompt = f"استخرج التاريخ فقط من الجملة التالية دون أي كلمات إضافية: {text}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أنت مساعد مختص باستخراج التواريخ فقط من النصوص."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content.strip()

@app.route("/analyze-intent", methods=["POST"])
def analyze_intent():
    user_input = request.json.get("message", "")
    system_msg = "حدد نية المستخدم من رده: (approve, redo, restart, fieldCorrection). إذا أراد تصحيح حقل، أذكر اسمه."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": user_input}
        ]
    )
    intent_text = response.choices[0].message.content.strip().lower()
    return jsonify({"intent": intent_text})

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    speech_file_path = os.path.join(tempfile.gettempdir(), "tts_output.mp3")
    response = client.audio.speech.create(model="tts-1", voice="nova", input=text)
    response.stream_to_file(speech_file_path)
    return send_file(speech_file_path, mimetype="audio/mpeg")

@app.route("/finalize", methods=["POST"])
def finalize_report():
    doc = DocxTemplate("police_report_template.docx")
    doc.render(session_data)
    output_path = os.path.join(tempfile.gettempdir(), "report.docx")
    doc.save(output_path)
    send_email("report.docx", output_path)
    session_data.clear()
    return jsonify({"message": "Report sent."})

def send_email(filename, file_path):
    msg = EmailMessage()
    msg["Subject"] = "تقرير فحص"
    msg["From"] = "bot@forensics.ai"
    msg["To"] = "recipient@example.com"
    msg.set_content("يرجى مراجعة التقرير المرفق.")
    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=filename)
    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login("bot@forensics.ai", os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
