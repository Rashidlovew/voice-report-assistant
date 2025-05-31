import os
import tempfile
from flask import Flask, request, send_from_directory, jsonify
from flask_cors import CORS
import openai
import requests
from pydub import AudioSegment
from werkzeug.utils import secure_filename

app = Flask(__name__)
CORS(app)
openai.api_key = os.environ.get("OPENAI_KEY")
ELEVENLABS_KEY = os.environ.get("ELEVENLABS_KEY")

FIELD_PROMPTS = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
}

@app.route("/")
def index():
    return send_from_directory("static", "index.html")

@app.route("/script.js")
def script():
    return send_from_directory("static", "script.js")

@app.route("/voice", methods=["POST"])
def handle_voice():
    file = request.files['audio']
    field = request.args.get("field") or ""
    filename = secure_filename(file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
        file.save(temp_webm.name)
        sound = AudioSegment.from_file(temp_webm.name)
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        sound.export(temp_wav.name, format="wav")

    with open(temp_wav.name, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ar"
        ).text

    gpt_prompt = f"""
    أعد صياغة النص التالي بطريقة مهنية لتضمينه في تقرير فني للشرطة مع الحفاظ على المعنى:

    "{transcript}"
    """
    completion = openai.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "user", "content": gpt_prompt}
        ]
    )
    rephrased = completion.choices[0].message.content.strip()

    # TTS with ElevenLabs
    tts_response = requests.post(
        "https://api.elevenlabs.io/v1/text-to-speech/AZnzlk1XvdvUeBnXmlld/stream",
        headers={
            "xi-api-key": ELEVENLABS_KEY,
            "Content-Type": "application/json"
        },
        json={
            "text": rephrased,
            "voice_settings": {"stability": 0.3, "similarity_boost": 0.8}
        }
    )

    audio_path = f"static/reply_{field}.mp3"
    with open(audio_path, "wb") as f:
        f.write(tts_response.content)

    return jsonify({
        "preview": rephrased,
        "audio_url": f"/reply_{field}.mp3"
    })

@app.route("/reply", methods=["POST"])
def handle_reply():
    file = request.files['audio']
    filename = secure_filename(file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_webm:
        file.save(temp_webm.name)
        sound = AudioSegment.from_file(temp_webm.name)
        temp_wav = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        sound.export(temp_wav.name, format="wav")

    with open(temp_wav.name, "rb") as audio_file:
        transcript = openai.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language="ar"
        ).text.strip()

    classify_prompt = f"""
    هل الجملة التالية تعني موافقة، تعديل، أم رفض؟ الجواب فقط بكلمة واحدة:
    الجملة: "{transcript}"
    الإجابة فقط: موافقة أو تعديل أو رفض
    """
    classification = openai.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": classify_prompt}]
    ).choices[0].message.content.strip()

    if "موافقة" in classification:
        return jsonify({"action": "accept"})
    elif "رفض" in classification:
        return jsonify({"action": "redo"})
    elif "تعديل" in classification or "أضف" in transcript:
        edit_prompt = f"عدل النص السابق بناءً على هذا التوجيه: {transcript}"
        edited = openai.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": edit_prompt}]
        ).choices[0].message.content.strip()
        return jsonify({"action": "edit", "modified_text": edited})

    return jsonify({"action": "unknown"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
