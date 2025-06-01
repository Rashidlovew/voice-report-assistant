from flask import Flask, request, send_file, jsonify
import os
import tempfile
import base64
import requests
from openai import OpenAI
from pydub import AudioSegment
from io import BytesIO
from docxtpl import DocxTemplate
from docx.shared import Pt
from docx.oxml.ns import qn

app = Flask(__name__)

# Load keys from environment
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
ELEVENLABS_KEY = os.environ["ELEVENLABS_KEY"]
EMAIL_SENDER = os.environ["EMAIL_SENDER"]
EMAIL_PASSWORD = os.environ["EMAIL_PASSWORD"]

client = OpenAI(api_key=OPENAI_API_KEY)

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

session_data = {
    "current_field": "Date",
    "responses": {}
}

@app.route("/start", methods=["POST"])
def start():
    session_data["current_field"] = "Date"
    session_data["responses"] = {}
    return jsonify({"prompt": field_prompts["Date"]})

@app.route("/fieldPrompt", methods=["GET"])
def get_prompt():
    field = session_data["current_field"]
    return jsonify({
        "prompt": field_prompts.get(field, "🎙️"),
        "field": field
    })

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    audio_data = request.json["audio"]
    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    audio = AudioSegment.from_file(BytesIO(audio_bytes), format="webm")
    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as temp_audio:
        audio.export(temp_audio.name, format="mp3")

        transcript = transcribe_audio(temp_audio.name)
        refined = refine_response(transcript, session_data["current_field"])
        session_data["responses"][session_data["current_field"]] = refined

        next_field = get_next_field(session_data["current_field"])
        if next_field:
            session_data["current_field"] = next_field
            speech = speak_text(field_prompts[next_field])
            return jsonify({
                "text": refined,
                "next_field": next_field,
                "audio": base64.b64encode(speech).decode()
            })
        else:
            doc_path = generate_report(session_data["responses"])
            return jsonify({
                "text": "✅ تم الانتهاء من جمع البيانات.",
                "done": True
            })

def transcribe_audio(file_path):
    with open(file_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="ar"
        )
    return response.text

def refine_response(transcript, field_name):
    field_ar = field_names_ar.get(field_name, field_name)
    prompt = f"لدي النص التالي المرتبط بـ {field_ar}:\n\"{transcript}\"\nرجاءً أعد صياغته بأسلوب تقرير شرطي احترافي باللغة العربية."
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    return response.choices[0].message.content.strip()

def get_next_field(current):
    keys = list(field_prompts.keys())
    idx = keys.index(current)
    return keys[idx + 1] if idx + 1 < len(keys) else None

def speak_text(text):
    response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/jN1a8k1Wv56Yf63YzCYr/stream",
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg"
        },
        json={
            "text": text,
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
            "output_format": "mp3_44100_128"
        }
    )
    return response.content

def generate_report(data):
    doc = DocxTemplate("police_report_template.docx")
    doc.render(data)
    output_path = "final_report.docx"
    doc.save(output_path)
    return output_path

@app.route("/")
def home():
    return send_file("templates/index.html")

@app.route("/static/<path:filename>")
def serve_static(filename):
    return send_file(f"static/{filename}")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
