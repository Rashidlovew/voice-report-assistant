const log = document.getElementById("log");
const fieldButtons = document.getElementById("field-buttons");

function appendLog(text) {
  const p = document.createElement("p");
  p.textContent = text;
  log.appendChild(p);
  log.scrollTop = log.scrollHeight;
}

let mediaRecorder;
let audioChunks = [];
let isRecording = false;
let silenceTimer;

document.getElementById("startButton").addEventListener("click", startConversation);

function startConversation() {
  appendLog("✅ بدء المحادثة...");
  fetch("/next")
    .then((res) => res.json())
    .then((data) => {
      appendLog("🗣️ المساعد: " + data.prompt);
      playAudio(data.audio_url);
      renderFieldButtons(data.fields);
    });
}

function renderFieldButtons(fields) {
  fieldButtons.innerHTML = "";
  if (!fields) return;
  Object.keys(fields).forEach((key) => {
    const btn = document.createElement("button");
    btn.textContent = `✏️ تعديل ${fields[key]}`;
    btn.onclick = () => {
      fetch(`/next?field=${key}`)
        .then((res) => res.json())
        .then((data) => {
          appendLog("🗣️ المساعد: " + data.prompt);
          playAudio(data.audio_url);
        });
    };
    fieldButtons.appendChild(btn);
  });
}

function playAudio(url) {
  const audio = new Audio(url);
  audio.play();
  audio.onended = startRecording;
}

function startRecording() {
  navigator.mediaDevices.getUserMedia({ audio: true }).then((stream) => {
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
      audioChunks.push(event.data);
    };

    mediaRecorder.onstop = () => {
      const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
      const formData = new FormData();
      formData.append("audio", audioBlob, "recording.webm");

      appendLog("⏳ جاري إرسال ردك...");
      fetch("/speak", {
        method: "POST",
        body: formData,
      })
        .then((res) => res.json())
        .then((data) => {
          appendLog("🧠 تمت المعالجة");
          appendLog("🗣️ المساعد: " + data.response);
          playAudio(data.audio_url);
          renderFieldButtons(data.fields);
        });
    };

    mediaRecorder.start();
    isRecording = true;
    appendLog("🎤 تسجيل صوتك...");

    silenceTimer = setTimeout(() => {
      stopRecording();
    }, 6000); // 6 ثواني للصمت
  });
}

function stopRecording() {
  if (isRecording && mediaRecorder) {
    clearTimeout(silenceTimer);
    mediaRecorder.stop();
    isRecording = false;
    appendLog("⏹️ توقف التسجيل.");
  }
}
