let mediaRecorder, audioChunks = [];

function logStatus(msg) {
  document.getElementById("status").innerText = msg;
  console.log("🔊", msg);
}

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
        logStatus("✅ تم إرسال التقرير");
        return;
      }

      const audioBlob = new Blob([new Uint8Array(data.audio)], { type: "audio/mpeg" });
      const audio = new Audio(URL.createObjectURL(audioBlob));

      document.getElementById("responseText").value = data.prompt;
      logStatus("🎧 استمع إلى: " + data.prompt);

      audio.onended = () => {
        logStatus("🎙️ جاري التسجيل...");
        listen();
      };

      audio.play().catch(error => {
        console.error("❌ Audio playback error:", error);
        logStatus("❌ لم يتم تشغيل الصوت.");
      });
    });
}

function listen() {
  audioChunks = [];

  navigator.mediaDevices.getUserMedia({ audio: true })
    .then(stream => {
      logStatus("🎙️ بدأ التسجيل...");
      mediaRecorder = new MediaRecorder(stream);
      mediaRecorder.start();

      mediaRecorder.ondataavailable = e => {
        console.log("📥 صوت تم تسجيله:", e.data);
        audioChunks.push(e.data);
      };

      mediaRecorder.onstop = () => {
        console.log("🛑 تم إيقاف التسجيل، عدد المقاطع:", audioChunks.length);
        if (audioChunks.length === 0) {
          logStatus("⚠️ لا يوجد صوت مسجل.");
        } else {
          sendReply();
        }
      };

      setTimeout(() => {
        mediaRecorder.stop();
      }, 5000);
    })
    .catch(err => {
      console.error("🎤 Microphone error:", err);
      logStatus("❌ لم يتم الوصول إلى المايكروفون!");
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
  logStatus("🔊 " + data.action);

  if (data.audio) {
    const audioBlob = new Blob([new Uint8Array(data.audio)], { type: "audio/mpeg" });
    const audio = new Audio(URL.createObjectURL(audioBlob));
    audio.onended = speakNextPrompt;
    audio.play().catch(error => {
      console.error("🔴 Failed to play audio:", error);
      logStatus("❌ لم يتم تشغيل الرد الصوتي.");
    });
  } else {
    speakNextPrompt();
  }
}
