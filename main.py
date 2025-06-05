import os
import base64
import tempfile
import openai
import smtplib
from flask import Flask, render_template, request, jsonify, send_file
from email.message import EmailMessage
from elevenlabs import generate, stream, set_api_key
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

app = Flask(__name__)
openai.api_key = os.getenv("OPENAI_API_KEY")
set_api_key(os.getenv("ELEVENLABS_KEY"))

EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER")

field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]
field_prompts = {
    "Date": "ما هو تاريخ الواقعة؟",
    "Briefing": "يرجى شرح موجز للواقعة.",
    "LocationObservations": "ما هي ملاحظاتك من معاينة الموقع؟",
    "Examination": "ما هي نتيجة الفحص الفني؟",
    "Outcomes": "ما النتيجة النهائية بعد الفحص؟",
    "TechincalOpinion": "ما هو رأيك الفني النهائي؟"
}
field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}
user_sessions = {}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    user_id = "default"
    session = user_sessions.setdefault(user_id, {"current_field": 0, "data": {}})
    current_field = field_order[session["current_field"]]

    audio_data = request.json["audio"]
    audio_binary = base64.b64decode(audio_data.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_binary)
        audio_path = f.name

    transcript = transcribe_audio(audio_path)
    os.remove(audio_path)

    if not transcript:
        return jsonify({"transcript": "", "response": "لم أتمكن من سماعك، حاول مرة أخرى."})

    intent = analyze_intent(transcript)

    if intent == "approve":
        session["current_field"] += 1
    elif intent == "redo":
        pass  # repeat same field
    elif intent == "restart":
        session["current_field"] = 0
        session["data"] = {}
    elif intent.startswith("field:"):
        field = intent.split(":")[1]
        if field in field_order:
            session["current_field"] = field_order.index(field)
    else:
        # Assume it's a real answer
        formalized = gpt_rephrase(transcript, field_names_ar[current_field])
        session["data"][current_field] = formalized
        session["current_field"] += 1

    if session["current_field"] >= len(field_order):
        file_path = generate_report_doc(session["data"])
        send_email(file_path)
        return jsonify({
            "transcript": transcript,
            "response": "📄 تم إنشاء التقرير وإرساله بالبريد الإلكتروني. شكراً لك!"
        })

    next_field = field_order[session["current_field"]]
    return jsonify({
        "transcript": transcript,
        "response": field_prompts[next_field]
    })

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    audio = generate(text=text, voice=os.getenv("ELEVEN_VOICE_ID", ""), stream=True)
    return stream(audio)

def transcribe_audio(path):
    with open(path, "rb") as f:
        transcript = openai.Audio.transcribe("whisper-1", f)
    return transcript.get("text", "")

def gpt_rephrase(text, field_ar):
    prompt = f"قم بصياغة هذا النص بشكل رسمي لتقرير شرطة، الحقل هو ({field_ar}): {text}"
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def analyze_intent(text):
    system_prompt = (
        "أنت مساعد ذكي يحلل نية المستخدم بناءً على رده الصوتي."
        "الرد يمكن أن يكون موافقة أو رفض أو طلب تكرار أو تصحيح حقل معين."
        "قم بإرجاع واحد فقط من التالي بدقة:\n"
        "- approve\n- redo\n- restart\n- field:<field_name>\n"
        "ولا تضف أي شيء آخر."
    )
    try:
        reply = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.2
        ).choices[0].message.content.strip()
        return reply
    except:
        return "redo"

def generate_report_doc(data):
    doc = Document("police_report_template.docx")
    for p in doc.paragraphs:
        for key, value in data.items():
            if f"{{{{{key}}}}}" in p.text:
                p.text = p.text.replace(f"{{{{{key}}}}}", value)
                p.runs[0].font.name = "Dubai"
                p.runs[0].font.size = Pt(13)
                p.runs[0]._element.rPr.rFonts.set(qn("w:eastAsia"), "Dubai")
                p.alignment = 2  # Right align
                p.paragraph_format.right_to_left = True
    output_path = "final_report.docx"
    doc.save(output_path)
    return output_path

def send_email(file_path):
    msg = EmailMessage()
    msg["Subject"] = "تم إنشاء تقرير جديد"
    msg["From"] = EMAIL_SENDER
    msg["To"] = EMAIL_RECEIVER
    msg.set_content("تم إنشاء تقرير جديد وإرفاقه بهذا البريد الإلكتروني.")

    with open(file_path, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename="police_report.docx")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

if __name__ == "__main__":
    app.run(debug=False, host="0.0.0.0", port=10000)
