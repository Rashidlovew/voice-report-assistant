import os
import base64
import tempfile
from flask import Flask, request, jsonify, render_template, send_file
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from openai import OpenAI
import smtplib
from email.message import EmailMessage

app = Flask(__name__, static_folder="static", template_folder="templates")
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Render HTML UI
@app.route('/')
def index():
    return render_template("index.html")

# Generate spoken audio response from text
@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    response = client.audio.speech.create(
        model="tts-1",
        voice="onyx",  # Change to "nova", "shimmer", etc. if preferred
        input=text
    )
    temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name
    with open(temp_path, "wb") as f:
        f.write(response.read())
    return send_file(temp_path, mimetype="audio/mpeg")

# Process recorded audio and generate report
@app.route("/submitAudio", methods=["POST"])
def handle_audio():
    data = request.get_json()
    audio_data = data["audio"].split(",")[1]  # Remove base64 header
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(base64.b64decode(audio_data))
        audio_path = f.name

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=open(audio_path, "rb"),
        response_format="text"
    )

    response_text = generate_response(transcript)

    if "report" in transcript.lower():
        report_path = generate_report(transcript)
        send_email(report_path)

    return jsonify({"transcript": transcript, "response": response_text})

# Use GPT to create a polite AI response
def generate_response(transcript):
    prompt = f"You are a polite assistant. Reply concisely in Arabic to: \"{transcript}\""
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a smart, polite Arabic voice assistant."},
            {"role": "user", "content": prompt}
        ]
    )
    return completion.choices[0].message.content.strip()

# Create Word document report
def generate_report(text):
    doc = Document("police_report_template.docx")

    for para in doc.paragraphs:
        for run in para.runs:
            if "{report_body}" in run.text:
                run.text = run.text.replace("{report_body}", text)
                set_rtl_style(run)

    output_path = "report_output.docx"
    doc.save(output_path)
    return output_path

# Email the generated report
def send_email(file_path):
    msg = EmailMessage()
    msg["Subject"] = "Automated Police Report"
    msg["From"] = os.environ["EMAIL_SENDER"]
    msg["To"] = os.environ["EMAIL_RECEIVER"]
    msg.set_content("Please find the generated report attached.")

    with open(file_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(file_path)
        msg.add_attachment(file_data, maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=file_name)

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(os.environ["EMAIL_USER"], os.environ["EMAIL_PASSWORD"])
        smtp.send_message(msg)

# Set RTL formatting for Arabic text in Word
def set_rtl_style(run):
    run.font.name = "Dubai"
    run.font.size = Pt(13)
    rPr = run._element.get_or_add_rPr()
    rtl = OxmlElement("w:rtl")
    rtl.set(qn("w:val"), "1")
    rPr.append(rtl)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
