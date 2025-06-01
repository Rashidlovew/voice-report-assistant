import os
import tempfile
from flask import Flask, request, render_template, jsonify, send_file
from openai import OpenAI
import requests

app = Flask(__name__)

# Load API keys from environment
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
ELEVENLABS_KEY = os.getenv("ELEVENLABS_KEY")
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

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    return jsonify({"status": "started"})

@app.route("/fieldPrompt")
def field_prompt():
    step = int(request.args.get("step", 0))
    fields = list(field_prompts.keys())

    if step >= len(fields):
        return jsonify({"done": True, "prompt": "", "fieldName": "", "audioUrl": ""})

    field_name = fields[step]
    prompt = field_prompts[field_name]
    spoken_mp3 = speak_text(prompt)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp:
        tmp.write(spoken_mp3)
        tmp.flush()
        temp_path = tmp.name

    return jsonify({
        "prompt": prompt,
        "fieldName": field_name,
        "audioUrl": f"/audio?path={temp_path}"
    })

@app.route("/audio")
def audio():
    path = request.args.get("path")
    if not os.path.exists(path):
        return "File not found", 404
    return send_file(path, mimetype="audio/mpeg")

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

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
