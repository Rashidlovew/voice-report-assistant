let mediaRecorder, audioChunks = [];

async function startConversation() {
  await fetch("/start", { method: "POST" });
  speakNextPrompt();
}

function speakNextPrompt() {
  fetch("/fieldPrompt")
    .then(res => res.json())
    .then(data => {
      if (data.done) {
        document.getElementById("status").innerText = "✅ تم إرسال التقرير";
        return;
      }
      const audio = new Audio(URL.createObjectURL(new Blob([new Uint8Array(data.audio.data)])));
      document.getElementById("responseText").value = data.prompt;
      document.getElementById("status").innerText = "🎧 استمع إلى: " + data.prompt;
      audio.onended = () => {
        document.getElementById("status").innerText = "🎙️ استمع لردك...";
        listen();
      };
      audio.play();
    });
}

async function listen() {
  audioChunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.start();

  mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

  setTimeout(() => {
    mediaRecorder.stop();
    mediaRecorder.onstop = sendReply;
  }, 5000);
}

async function sendReply() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("audio", audioBlob);
  const res = await fetch("/listen", { method: "POST", body: formData });
  const data = await res.json();

  document.getElementById("responseText").value = data.text;
  document.getElementById("status").innerText = "🔊 " + data.action;

  if (data.audio) {
    const audio = new Audio(URL.createObjectURL(new Blob([new Uint8Array(data.audio.data)])));
    audio.onended = speakNextPrompt;
    audio.play();
  } else {
    speakNextPrompt();
  }
}

startConversation();
