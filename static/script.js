let mediaRecorder;
let audioChunks = [];

window.onload = async () => {
  const res = await fetch("/next");
  const data = await res.json();
  speakAndDisplay(data.text);
};

async function speakAndDisplay(text) {
  document.getElementById("response").innerText = text;
  const response = await fetch("/speak", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({ text })
  });
  const audioBlob = await response.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
}

function startRecording() {
  navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = event => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
      const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
      const formData = new FormData();
      formData.append("audio", audioBlob);

      // Send audio to Whisper
      const whisperResponse = await fetch("https://api.openai.com/v1/audio/transcriptions", {
        method: "POST",
        headers: {
          Authorization: "Bearer " + OPENAI_API_KEY, // ⚠️ Replace if not injected from backend
        },
        body: formData
      });

      const whisperData = await whisperResponse.json();
      const transcript = whisperData.text;

      const replyRes = await fetch("/reply", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({ text: transcript })
      });
      const replyData = await replyRes.json();

      if (replyData.next) {
        speakAndDisplay(replyData.text);
      } else if (replyData.done) {
        document.getElementById("response").innerText = "✅ تم استلام كل البيانات. شكرًا لك!";
      }
    };

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000); // التسجيل لـ 5 ثواني فقط
  });
}
