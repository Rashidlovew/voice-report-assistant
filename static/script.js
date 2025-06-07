let currentField = "Date";

async function fetchPrompt() {
  const res = await fetch("/next");
  const data = await res.json();
  if (data.done) {
    speak("✅ تم الانتهاء من جميع الحقول. شكراً لك.");
    return;
  }
  currentField = data.field;
  speak(data.prompt);
}

async function speak(text) {
  const res = await fetch("/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const audioBlob = await res.blob();
  const audioUrl = URL.createObjectURL(audioBlob);
  const audio = new Audio(audioUrl);
  audio.play();
}

async function sendAudio(base64Audio) {
  const res = await fetch("/transcribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audio: base64Audio, field: currentField }),
  });
  const data = await res.json();
  if (data.text) {
    document.getElementById("result").innerHTML += `<p><b>${currentField}:</b> ${data.text}</p>`;
    fetchPrompt();
  } else {
    speak("حدث خطأ، حاول مرة أخرى.");
  }
}

let mediaRecorder;
let chunks = [];

document.getElementById("startBtn").onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = (e) => {
    chunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    const reader = new FileReader();
    reader.onloadend = () => {
      sendAudio(reader.result);
    };
    reader.readAsDataURL(blob);
    chunks = [];
  };

  mediaRecorder.start();
  speak("🎤 التسجيل بدأ الآن...");
};

document.getElementById("stopBtn").onclick = () => {
  mediaRecorder.stop();
  speak("⏹️ تم إيقاف التسجيل.");
};

window.onload = fetchPrompt;
