import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, Voice, VoiceSettings, set_api_key
from docxtpl import DocxTemplate

# Set up environment
app = Flask(__name__)
CORS(app)

# ✅ Initialize APIs
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# ✅ Choose the best Arabic-compatible ElevenLabs voice
voice = Voice(
    voice_id="EXAVITQu4vr4xnSDxMaL",  # "Hala" voice (Arabic-compatible)
    settings=VoiceSettings(stability=0.4, similarity_boost=0.9)
)

# ✅ User session storage
user_session = {
    "current_field": "Date",
    "fields": {}
}

# ✅ Report fields and Arabic prompts
field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]

field_prompts = {
    "Date": "📅 من فضلك أخبرني بتاريخ الواقعة.",
    "Briefing": "📝 ما هو موجز الحادث؟",
    "LocationObservations": "📍 صف لي ملاحظاتك حول موقع الحادث.",
    "Examination": "🔬 ما هي نتائج الفحص الفني؟",
    "Outcomes": "📌 ما هي النتيجة النهائية بناءً على الفحص؟",
    "TechincalOpinion": "💡 ما هو رأيك الفني في الحادث؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص الفني",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}

# ✅ Generate voice from text using ElevenLabs
def speak_text(text):
    audio = generate(text=text, voice=voice)
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_file.write(audio)
    temp_file.close()
    return temp_file.name

# ✅ Rephrase and summarize Arabic text using OpenAI
def rephrase_text(text, field):
    prompt = f"""
أعد صياغة النص التالي ليكون أكثر رسمية واحترافية لتقرير شرطة:

النص:
{text}

— الحقل: {field_names_ar.get(field, field)}
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4
    )
    return response.choices[0].message.content.strip()

# ✅ Route to serve voice response
@app.route("/speak", methods=["POST"])
def handle_speak():
    data = request.json
    text = data.get("text", "")
    audio_path = speak_text(text)
    return send_file(audio_path, mimetype="audio/mpeg")

# ✅ Route to get next field prompt
@app.route("/next", methods=["GET"])
def next_prompt():
    current = user_session["current_field"]
    fields = user_session["fields"]

    if current not in fields:
        prompt = field_prompts.get(current, "🎙️ تحدث الآن.")
        return jsonify({"field": current, "prompt": prompt})

    current_index = field_order.index(current)
    if current_index + 1 >= len(field_order):
        return jsonify({"done": True, "message": "✅ تم استلام جميع الحقول. يتم الآن تجهيز التقرير..."})

    next_field = field_order[current_index + 1]
    user_session["current_field"] = next_field
    prompt = field_prompts[next_field]
    return jsonify({"field": next_field, "prompt": prompt})

# ✅ Route to submit audio transcription (replace this with real Whisper logic)
@app.route("/submit", methods=["POST"])
def submit_transcription():
    data = request.json
    text = data.get("text", "")
    field = user_session["current_field"]

    refined = rephrase_text(text, field)
    user_session["fields"][field] = refined

    return jsonify({
        "saved": True,
        "field": field,
        "value": refined
    })

# ✅ Route to generate and download Word report
@app.route("/report", methods=["GET"])
def generate_report():
    tpl = DocxTemplate("police_report_template.docx")
    tpl.render(user_session["fields"])
    output_path = "final_report.docx"
    tpl.save(output_path)
    return send_file(output_path, as_attachment=True)

# ✅ Greeting route
@app.route("/", methods=["GET"])
def greet():
    greeting_text = "مرحباً بك في مساعد إنشاء التقارير الخاص بقسم الهندسة الجنائية. 🎙️"
    audio_path = speak_text(greeting_text)
    return send_file(audio_path, mimetype="audio/mpeg")

if __name__ == "__main__":
    print("✅ OpenAI version:", OpenAI.__module__)
    app.run(host="0.0.0.0", port=10000)
