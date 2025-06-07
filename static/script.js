let mediaRecorder;
let chunks = [];
let currentField = "Date";

// تحميل أول سؤال
window.onload = async () => {
  const res = await fetch("/next");
  const data = await res.json();
  currentField = data.field;
  speak(data.prompt);
};

// زر بدء التسجيل
document.getElementById("startBtn").onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  chunks = [];

  mediaRecorder.ondataavailable = (e) => {
    if (e.data.size > 0) chunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    const blob = new Blob(chunks, { type: "audio/webm" });
    const reader = new FileReader();
    reader.onloadend = () => {
      sendAudio(reader.result);
    };
    reader.readAsDataURL(blob);
  };

  mediaRecorder.start();
  speak("🎤 تم بدء التسجيل. تحدث الآن لمدة 6 ثوانٍ...");
  setTimeout(() => mediaRecorder.stop(), 6000);
};

// زر الإيقاف اليدوي
document.getElementById("stopBtn").onclick = () => {
  if (mediaRecorder && mediaRecorder.state === "recording") {
    mediaRecorder.stop();
    speak("⏹️ تم إيقاف التسجيل.");
  }
};

// إرسال الصوت إلى /transcribe
async function sendAudio(base64Audio) {
  const res = await fetch("/transcribe", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ audio: base64Audio, field: currentField }),
  });
  const data = await res.json();
  if (data.text) {
    showResult(currentField, data.text);
    speak(data.text);
    await delay(3000);
    askNext();
  } else {
    speak("حدث خطأ أثناء المعالجة.");
  }
}

// عرض الرد
function showResult(field, value) {
  const container = document.getElementById("result");
  container.innerHTML += `<p><b>${field}:</b> ${value}</p>`;
}

// طلب الحقل التالي
async function askNext() {
  const res = await fetch("/next");
  const data = await res.json();
  if (data.done) {
    speak("✅ تم الانتهاء من جميع الحقول. شكراً لك.");
  } else {
    currentField = data.field;
    speak(data.prompt);
  }
}

// تشغيل صوت من الخادم
async function speak(text) {
  const res = await fetch("/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  });
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const audio = new Audio(url);
  audio.play();
}

// تأخير بسيط
function delay(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}
