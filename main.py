import openai
print("✅ OpenAI version:", openai.__version__)

import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from openai import OpenAI

# إعداد OpenAI client بدون تمرير proxies
client = OpenAI()

# بعد إنشاء العميل، نستدعي ElevenLabs
from elevenlabs import Voice, VoiceSettings, set_api_key, generate
set_api_key(os.getenv("ELEVENLABS_API_KEY"))

from docxtpl import DocxTemplate
from pydub import AudioSegment
import smtplib
from email.message import EmailMessage

app = Flask(__name__)
CORS(app)

# تخزين الجلسة
user_session = {
    "current_field": "Date",
    "fields": {}
}

field_order = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"]

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

@app.route("/")
def index():
    return "✅ Arabic Voice Report Assistant is running."

@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    audio = generate(
        text=text,
        voice=Voice(
            voice_id="EXAVITQu4vr4xnSDxMaL",  # Rachel's voice
            settings=VoiceSettings(stability=0.5, similarity_boost=0.75)
        )
    )
    return audio, 200, {"Content-Type": "audio/mpeg"}

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_file:
        audio_path = temp_file.name
        audio_file.save(audio_path)

    audio = AudioSegment.from_file(audio_path)
    wav_path = audio_path.replace(".webm", ".wav")
    audio.export(wav_path, format="wav")

    with open(wav_path, "rb") as f:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=f
        ).text

    # Rephrase the transcription using ChatGPT
    completion = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "أعد صياغة هذا النص بصيغة تقرير شرطي رسمية باللغة العربية."},
            {"role": "user", "content": transcript}
        ]
    )

    rephrased_text = completion.choices[0].message.content
    current_field = user_session["current_field"]
    user_session["fields"][current_field] = rephrased_text

    # الإنتقال للسؤال التالي
    next_index = field_order.index(current_field) + 1
    if next_index < len(field_order):
        next_field = field_order[next_index]
        user_session["current_field"] = next_field
        return jsonify({
            "transcript": transcript,
            "rephrased": rephrased_text,
            "next_prompt": field_prompts[next_field]
        })
    else:
        return jsonify({
            "transcript": transcript,
            "rephrased": rephrased_text,
            "next_prompt": None  # End of flow
        })

@app.route("/generateReport", methods=["GET"])
def generate_report():
    doc = DocxTemplate("police_report_template.docx")
    doc.render(user_session["fields"])
    output_path = "/tmp/final_report.docx"
    doc.save(output_path)

    # إرسال التقرير بالإيميل
    send_report_by_email(output_path)

    return send_file(output_path, as_attachment=True)

def send_report_by_email(file_path):
    msg = EmailMessage()
    msg["Subject"] = "📄 التقرير الفني من المساعد الصوتي"
    msg["From"] = "noreply@voice-assistant.com"
    msg["To"] = "frnreports@gmail.com"
    msg.set_content("تم إنشاء التقرير بنجاح وإرفاقه في هذا البريد.\n\nتحياتنا.")

    with open(file_path, "rb") as f:
        file_data = f.read()
        file_name = os.path.basename(file_path)

    msg.add_attachment(file_data, maintype="application", subtype="vnd.openxmlformats-officedocument.wordprocessingml.document", filename=file_name)

    with smtplib.SMTP("smtp.gmail.com", 587) as smtp:
        smtp.starttls()
        smtp.login(os.getenv("EMAIL_USERNAME"), os.getenv("EMAIL_PASSWORD"))
        smtp.send_message(msg)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
