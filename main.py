import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, set_api_key, Voice, VoiceSettings

app = Flask(__name__)
CORS(app)

# ✅ إعداد المفاتيح
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

# ✅ بيانات الجلسة
user_session = {
    "current_field": "Date",
    "fields": {},
}

# ✅ ترتيب الحقول والمطالبات
field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]

field_prompts = {
    "Date": "📅 ما هو تاريخ الواقعة؟",
    "Briefing": "📝 ما هو موجز الواقعة؟",
    "LocationObservations": "👁️ ماذا لاحظت أثناء معاينة الموقع؟",
    "Examination": "🔬 ما هي نتيجة الفحص الفني؟",
    "Outcomes": "📌 ما هي النتيجة النهائية؟",
    "TechincalOpinion": "🧠 ما هو رأيك الفني؟"
}

# ✅ الصفحة الرئيسية
@app.route("/")
def index():
    return send_file("index.html")

# ✅ تشغيل الصوت باستخدام ElevenLabs (Rachel)
def text_to_speech(text):
    audio = generate(
        text=text,
        voice=Voice(
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
            settings=VoiceSettings(stability=0.5, similarity_boost=0.85)
        )
    )
    temp_path = tempfile.mktemp(suffix=".mp3")
    with open(temp_path, "wb") as f:
        f.write(audio)
    return temp_path

# ✅ API: /speak
@app.route("/speak", methods=["POST"])
def speak():
    text = request.json.get("text")
    if not text:
        return jsonify({"error": "No text provided"}), 400
    try:
        path = text_to_speech(text)
        return send_file(path, mimetype="audio/mpeg")
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ API: /next — استرجاع الحقل التالي
@app.route("/next", methods=["GET"])
def next_field():
    current = user_session["current_field"]
    idx = field_order.index(current)
    if idx + 1 < len(field_order):
        next_f = field_order[idx + 1]
        user_session["current_field"] = next_f
        return jsonify({"field": next_f, "prompt": field_prompts[next_f]})
    else:
        return jsonify({"done": True})

# ✅ API: /reset — إعادة ضبط الجلسة
@app.route("/reset", methods=["POST"])
def reset():
    user_session["current_field"] = "Date"
    user_session["fields"] = {}
    return jsonify({"message": "🔄 تم إعادة ضبط الجلسة."})

# ✅ API: /inputs — عرض المدخلات
@app.route("/inputs", methods=["GET"])
def get_inputs():
    return jsonify(user_session["fields"])

# ✅ API: /transcribe — استقبال الصوت وتحويله لنص وإعادة صياغته
@app.route("/transcribe", methods=["POST"])
def transcribe():
    audio_data = request.json.get("audio")
    field = request.json.get("field")
    if not audio_data or not field:
        return jsonify({"error": "بيانات ناقصة"}), 400

    audio_bytes = base64.b64decode(audio_data.split(",")[1])
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        f.write(audio_bytes)
        f.flush()
        audio_path = f.name

    try:
        # تحويل الصوت لنص
        text = client.audio.transcriptions.create(
            file=open(audio_path, "rb"),
            model="whisper-1",
            response_format="text",
            language="ar"
        )

        # إعادة الصياغة
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "أعد صياغة هذا الرد بأسلوب مهني لتقرير شرطة."},
                {"role": "user", "content": text}
            ]
        )
        rephrased = response.choices[0].message.content.strip()
        user_session["fields"][field] = rephrased
        return jsonify({"text": rephrased})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ✅ تشغيل السيرفر في Render
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
