import os
import tempfile
import base64
import ffmpeg
from flask import Flask, request, jsonify
from flask_cors import CORS
from openai import OpenAI
from elevenlabs import generate, Voice, VoiceSettings, set_api_key
from docxtpl import DocxTemplate

# إعداد Flask
app = Flask(__name__)
CORS(app)

# مفاتيح API
openai_key = os.getenv("OPENAI_API_KEY")
eleven_key = os.getenv("ELEVENLABS_API_KEY")
set_api_key(eleven_key)
client = OpenAI(api_key=openai_key)

# الجلسة
user_session = {
    "current_field": None,
    "fields": {},
    "last_prompt": "",
}

# الحقول وتعريفاتها
field_prompts = {
    "Date": "🎙️ ما هو تاريخ الواقعة؟",
    "Briefing": "🎙️ أخبرني بموجز الواقعة.",
    "LocationObservations": "🎙️ ماذا لاحظت عند معاينة موقع الحادث؟",
    "Examination": "🎙️ ما نتيجة الفحص الفني؟",
    "Outcomes": "🎙️ ما هي النتيجة النهائية بعد الفحص؟",
    "TechincalOpinion": "🎙️ ما هو رأيك الفني النهائي؟"
}

field_names_ar = {
    "Date": "التاريخ",
    "Briefing": "موجز الواقعة",
    "LocationObservations": "معاينة الموقع",
    "Examination": "نتيجة الفحص",
    "Outcomes": "النتيجة",
    "TechincalOpinion": "الرأي الفني"
}


def transcribe_audio(file_path):
    mp3_path = tempfile.mktemp(suffix=".mp3")
    ffmpeg.input(file_path).output(mp3_path).run(overwrite_output=True)
    with open(mp3_path, "rb") as f:
        transcript = client.audio.transcriptions.create(model="whisper-1", file=f)
    return transcript.text.strip()


def rephrase_text(text):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أعد صياغة هذا الكلام بأسلوب رسمي لتقرير فني للشرطة باللغة العربية:"},
            {"role": "user", "content": text}
        ]
    )
    return response.choices[0].message.content.strip()


def detect_intent(text):
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "مهمتك أن تحدد نية المتحدث بدقة. اختر فقط واحدة من: 'approve' للموافقة، 'redo' للإعادة، 'append' للإضافة أو 'unknown' إن لم تفهم."},
            {"role": "user", "content": f"الرد: {text}"}
        ]
    )
    return response.choices[0].message.content.strip()


def get_next_prompt(current_field):
    fields = list(field_prompts.keys())
    try:
        idx = fields.index(current_field)
        return fields[idx + 1] if idx + 1 < len(fields) else None
    except ValueError:
        return fields[0]  # بداية


def speak_text(text):
    audio = generate(
        text=text,
        voice=Voice(voice_id="EXAVITQu4vr4xnSDxMaL", settings=VoiceSettings(stability=0.5, similarity_boost=0.8))
    )
    return audio


@app.route("/next", methods=["GET"])
def next_prompt():
    if not user_session["current_field"]:
        user_session["current_field"] = list(field_prompts.keys())[0]

    field = user_session["current_field"]
    prompt = field_prompts[field]
    user_session["last_prompt"] = prompt
    audio = speak_text(prompt)
    return jsonify({"prompt": prompt, "audio": base64.b64encode(audio).decode("utf-8")})


@app.route("/speak", methods=["POST"])
def process_voice():
    audio_data = request.files["audio"]
    with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp:
        audio_data.save(temp.name)
        temp_path = temp.name

    # تحويل إلى نص
    transcript = transcribe_audio(temp_path)
    intent = detect_intent(transcript)

    current_field = user_session["current_field"]

    if intent == "redo":
        response = speak_text("🔁 حسنًا، كرر الإجابة من فضلك.")
        return jsonify({"redo": True, "audio": base64.b64encode(response).decode("utf-8")})

    elif intent == "append":
        addition = rephrase_text(transcript)
        user_session["fields"][current_field] += " " + addition
        response = speak_text("📌 تمت إضافة المعلومة، هل ترغب في المتابعة؟")
        return jsonify({"append": True, "audio": base64.b64encode(response).decode("utf-8")})

    elif intent == "approve" or intent == "unknown":
        refined = rephrase_text(transcript)
        user_session["fields"][current_field] = refined

        next_field = get_next_prompt(current_field)
        if next_field:
            user_session["current_field"] = next_field
            prompt = field_prompts[next_field]
            user_session["last_prompt"] = prompt
            audio = speak_text(prompt)
            return jsonify({"field_saved": True, "next_field": next_field, "audio": base64.b64encode(audio).decode("utf-8")})
        else:
            # تم الانتهاء
            create_report(user_session["fields"])
            response = speak_text("✅ تم إنشاء التقرير بنجاح وتم إرساله إلى البريد.")
            return jsonify({"done": True, "audio": base64.b64encode(response).decode("utf-8")})

    else:
        error_audio = speak_text("❗ لم أفهم، هل يمكنك التوضيح؟")
        return jsonify({"error": True, "audio": base64.b64encode(error_audio).decode("utf-8")})


def create_report(fields):
    doc = DocxTemplate("police_report_template.docx")
    doc.render(fields)
    output_path = "/tmp/final_report.docx"
    doc.save(output_path)

    # إرسال الإيميل (اختياري - placeholder فقط)
    send_email(output_path)


def send_email(file_path):
    # استخدم SMTP لإرسال التقرير
    print(f"📤 Sending report from {file_path} to frnreports@gmail.com ... (mocked)")  # ضع هنا تنفيذ البريد الحقيقي عند الحاجة


@app.route("/")
def index():
    return "✅ Voice Assistant is running."


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
