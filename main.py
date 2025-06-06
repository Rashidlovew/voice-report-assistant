import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from docx import Document
from docx.shared import Pt
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

app = Flask(__name__)
CORS(app)

# Load OpenAI API key from environment variable
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Load the report template
TEMPLATE_PATH = "police_report_template.docx"
DEFAULT_EMAIL = "frnreports@gmail.com"

# Arabic field prompts (formal female tone)
field_prompts = {
    "Date": "🎙️ من فضلك، أخبريني بتاريخ الواقعة.",
    "Briefing": "🎙️ يرجى تزويدي بموجز حول الواقعة.",
    "LocationObservations": "🎙️ كيف كانت معاينة الموقع؟ يرجى التوضيح بالتفصيل.",
    "Examination": "🎙️ ما هي نتيجة الفحص الفني؟",
    "Outcomes": "🎙️ ما هي النتيجة بعد الفحص والمعاينة؟",
    "TechincalOpinion": "🎙️ ما هو الرأي الفني في هذه الحالة؟"
}

# Field names in Arabic for document placeholders
field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

# In-memory session store
user_sessions = {}

# Format text in right-to-left, right-aligned Arabic
def format_paragraph(paragraph):
    run = paragraph.runs[0]
    run.font.name = 'Dubai'
    run._element.rPr.rFonts.set(qn('w:eastAsia'), 'Dubai')
    run.font.size = Pt(13)
    paragraph.alignment = 2  # Right aligned
    paragraph.paragraph_format.right_to_left = True

# Fill the Word document with Arabic placeholders
def generate_report(field_data):
    doc = Document(TEMPLATE_PATH)
    for paragraph in doc.paragraphs:
        for key, value in field_data.items():
            placeholder = f"{{{{{key}}}}}"
            if placeholder in paragraph.text:
                paragraph.text = paragraph.text.replace(placeholder, value)
                format_paragraph(paragraph)
    output_path = tempfile.NamedTemporaryFile(delete=False, suffix=".docx").name
    doc.save(output_path)
    return output_path

# Analyze intent using OpenAI
def analyze_intent(user_input):
    prompt = f"""
أنت مساعد ذكي يتعرف على نية المستخدم بناءً على الرد.
الرد: "{user_input}"

ما هي نية المستخدم؟ اختر واحدة فقط:
- approve (إذا وافق على النص)
- redo (إذا أراد إعادة الإدخال)
- restart (إذا أراد البدء من جديد)
- fieldCorrection (إذا أراد إعادة حقل معين)

النية:
"""
    completion = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )
    result = completion.choices[0].message.content.strip().lower()
    return result

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    speech = client.audio.speech.create(model="tts-1", voice="shimmer", input=text)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    speech.stream_to_file(temp_file.name)
    return send_file(temp_file.name, mimetype="audio/mpeg")

@app.route("/submitAudio", methods=["POST"])
def handle_audio():
    data = request.get_json()
    audio_base64 = data["audio"].split(",")[1]
    audio_bytes = base64.b64decode(audio_base64)
    temp_audio = tempfile.NamedTemporaryFile(delete=False, suffix=".webm")
    temp_audio.write(audio_bytes)
    temp_audio.close()

    # Transcribe audio
    with open(temp_audio.name, "rb") as f:
        transcript_response = client.audio.transcriptions.create(model="whisper-1", file=f)
        transcript_text = transcript_response.text.strip()

    user_id = "default_user"
    session = user_sessions.setdefault(user_id, {"step": 0, "fields": {}})

    current_step = session["step"]
    current_field = list(field_prompts.keys())[current_step]

    # Analyze response
    intent = analyze_intent(transcript_text)

    if intent == "redo":
        reply = f"↩️ لا بأس، يرجى إعادة {field_names_ar[current_field]}."
        return jsonify({"transcript": transcript_text, "response": reply})

    elif intent == "restart":
        user_sessions[user_id] = {"step": 0, "fields": {}}
        first_prompt = list(field_prompts.values())[0]
        return jsonify({"transcript": transcript_text, "response": f"🔄 تم البدء من جديد. {first_prompt}"})

    elif intent == "fieldCorrection":
        reply = "↩️ يرجى تحديد الحقل الذي ترغب في تعديله."
        return jsonify({"transcript": transcript_text, "response": reply})

    # Save field and continue
    session["fields"][current_field] = transcript_text
    session["step"] += 1

    if session["step"] >= len(field_prompts):
        doc_path = generate_report(session["fields"])
        session.clear()
        return jsonify({
            "transcript": transcript_text,
            "response": "✅ تم إنشاء التقرير بنجاح. سيتم إرساله إلى البريد الإلكتروني.",
            "download_url": "/download-report?path=" + doc_path
        })

    next_field = list(field_prompts.keys())[session["step"]]
    return jsonify({"transcript": transcript_text, "response": field_prompts[next_field]})

@app.route("/download-report")
def download_report():
    path = request.args.get("path")
    if not path or not os.path.exists(path):
        return "Report not found", 404
    return send_file(path, as_attachment=True)

@app.route("/")
def home():
    return "Voice Report Assistant is running."

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
