import os
import tempfile
import requests
from flask import Flask, request, jsonify, render_template
from pydub import AudioSegment
from openai import OpenAI

# Environment variables
OPENAI_KEY = os.environ["OPENAI_KEY"]
ELEVENLABS_KEY = os.environ["ELEVENLABS_KEY"]

app = Flask(__name__)
client = OpenAI(api_key=OPENAI_KEY)

field_prompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
}
expected_fields = list(field_prompts.keys())
user_state = {"step_index": 0}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/start", methods=["POST"])
def start():
    user_state["step_index"] = 0
    return field_prompt()

@app.route("/fieldPrompt")
def field_prompt():
    index = user_state["step_index"]
    if index >= len(expected_fields):
        return jsonify({"prompt": "✅ انتهت الحقول.", "audio": []})
    field = expected_fields[index]
    prompt = field_prompts[field]
    audio = speak_text(prompt)
    return jsonify({"prompt": prompt, "audio": list(audio)})

@app.route("/listen", methods=["POST"])
def listen():
    index = user_state["step_index"]
    if index >= len(expected_fields):
        return jsonify({"text": "", "prompt": "✅ انتهت الحقول.", "audio": []})

    audio_file = request.files["audio"]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        audio_file.save(tmp.name)
        sound = AudioSegment.from_file(tmp.name)
        wav_path = tmp.name + ".wav"
        sound.export(wav_path, format="wav")
        with open(wav_path, "rb") as f:
            transcript = client.audio.transcriptions.create(model="whisper-1", file=f, language="ar")

    field = expected_fields[index]
    user_state["step_index"] += 1
    rephrased = enhance_with_gpt(field, transcript.text)
    next_prompt = field_prompts[expected_fields[user_state["step_index"]]] if user_state["step_index"] < len(expected_fields) else "✅ انتهت الحقول."
    audio = speak_text(next_prompt)
    return jsonify({"text": rephrased, "prompt": next_prompt, "audio": list(audio)})

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

def enhance_with_gpt(field, user_input):
    prompt = f"أعد صياغة النص التالي ({field}) بلغة عربية فصحى ورسمية بدون تغيير المعنى:\n\n{user_input}"
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
