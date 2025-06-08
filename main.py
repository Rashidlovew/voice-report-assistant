import os
import base64
import tempfile
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS
from werkzeug.utils import secure_filename
import openai

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/submitAudio", methods=["POST"])
def submit_audio():
    data = request.get_json()
    audio_data = data["audio"].split(",")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as temp_audio:
        temp_audio.write(base64.b64decode(audio_data))
        temp_audio_path = temp_audio.name

    with open(temp_audio_path, "rb") as audio_file:
        transcript = openai.Audio.transcribe("whisper-1", audio_file)

    user_text = transcript["text"]

    chat_completion = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "قم بإعادة صياغة هذا النص بأسلوب رسمي ومهني لتقرير شرطة:"},
            {"role": "user", "content": user_text}
        ]
    )
    response_text = chat_completion.choices[0].message.content.strip()

    return jsonify({"response": response_text})


@app.route("/stream-audio")
def stream_audio():
    text = request.args.get("text", "")
    speech_file_path = os.path.join(tempfile.gettempdir(), "openai_speech.mp3")

    response = openai.Audio.speech.create(
        model="tts-1",
        voice="nova",  # can be 'onyx', 'echo', 'nova', or 'shimmer'
        input=text
    )

    response.stream_to_file(speech_file_path)
    return send_file(speech_file_path, mimetype="audio/mpeg")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
