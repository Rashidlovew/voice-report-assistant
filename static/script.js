let mediaRecorder, audioChunks = [];

function startConversation() {
  fetch("/start", { method: "POST" }).then(() => {
    speakNextPrompt();
  });
}

function speakNextPrompt() {
  fetch("/fieldPrompt")
    .then(res => res.json())
    .then(data => {
      if (data.done) {
        document.getElementById("status").innerText = "✅ تم إرسال التقرير";
        return;
      }

      const audioBlob = new Blob([new Uint8Array(data.audio)], { type: "audio/mpeg" });
      const audio = new Audio(URL.createObjectURL(audioBlob));

      document.getElementById("responseText").value = data.prompt;
      document.getElementById("status").innerText = "🎧 استمع إلى: " + data.prompt;

      audio.onended = () => {
        document.getElementById("status").innerText = "🎙️ جاري التسجيل...";
        listen();
      };

      audio.play().catch(error => {
        console.error("🔴 Failed to play audio:", error);
        document.getElementById("status").innerText = "❌ لم يتم تشغيل الصوت.";
      });
    });
}

function listen() {
  audioChunks = [];
  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      document.getElementById("status").innerText = "🎙️ جاري التسجيل...";
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.start();

      mediaRecorder.ondataavailable = e => audioChunks.push(e.data);

      setTimeout(() => {
        mediaRecorder.stop();
        mediaRecorder.onstop = sendReply;
      }, 5000);
    })
    .catch(err => {
      console.error("🎤 Microphone error:", err);
      document.getElementById("status").innerText = "❌ لم يتم تشغيل المايك!";
    });
}

async function sendReply() {
  const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
  const formData = new FormData();
  formData.append("audio", audioBlob);

  const res = await fetch("/listen", {
    method: "POST",
    body: formData
  });

  const data = await res.json();
  document.getElementById("responseText").value = data.text || "";
  document.getElementById("status").innerText = "🔊 " + data.action;

  if (data.audio) {
    const audioBlob = new Blob([new Uint8Array(data.audio)], { type: "audio/mpeg" });
    const audio = new Audio(URL.createObjectURL(audioBlob));
    audio.onended = speakNextPrompt;
    audio.play().catch(error => {
      console.error("🔴 Failed to play audio:", error);
      document.getElementById("status").innerText = "❌ لم يتم تشغيل الرد الصوتي.";
    });
  } else {
    speakNextPrompt();
  }
}
