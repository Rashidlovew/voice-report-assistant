let mediaRecorder;
let audioChunks = [];
let currentField = "";
const startBtn = document.getElementById("startBtn");
const promptText = document.getElementById("prompt");
const rephrasedText = document.getElementById("rephrased");

window.onload = async () => {
  const res = await fetch("/start");
  const data = await res.json();
  currentField = data.nextField;
  promptText.innerText = data.prompt;
};

startBtn.onclick = async () => {
  startBtn.disabled = true;
  rephrasedText.innerText = "🔊 جاري التسجيل...";

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = (event) => {
    if (event.data.size > 0) audioChunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const reader = new FileReader();
    reader.onloadend = async () => {
      const base64data = reader.result;
      const res = await fetch("/upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: base64data }),
      });
      const result = await res.json();

      if (result.done) {
        promptText.innerText = "✅ جاري إنشاء التقرير...";
        await fetch("/generate-report");
        rephrasedText.innerText = "📩 تم إرسال التقرير إلى البريد.";
        return;
      }

      currentField = result.nextField;
      promptText.innerText = result.prompt;
      rephrasedText.innerText = `✍️ إعادة الصياغة:\n${result.rephrased}`;

      // تشغيل الرد الصوتي
      const audioRes = await fetch("/stream-audio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: result.rephrased }),
      });
      const audioBlob = await audioRes.blob();
      const audioUrl = URL.createObjectURL(audioBlob);
      const audio = new Audio(audioUrl);
      audio.play();
    };
    reader.readAsDataURL(audioBlob);
  };

  mediaRecorder.start();
  setTimeout(() => mediaRecorder.stop(), 6000);
};
