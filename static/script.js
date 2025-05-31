let mediaRecorder;
let audioChunks = [];

document.getElementById("recordBtn").onclick = async () => {
  audioChunks = [];
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  mediaRecorder.start();
  document.getElementById("status").innerText = "🎙️ جاري التسجيل...";

  mediaRecorder.ondataavailable = e => {
    audioChunks.push(e.data);
  };

  mediaRecorder.onstop = async () => {
    const field = document.getElementById("field").value;
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob);
    formData.append("field", field);

    document.getElementById("status").innerText = "🔁 جاري المعالجة...";

    const response = await fetch("/voice", { method: "POST", body: formData });
    const result = await response.json();
    document.getElementById("responseText").value = result.text;
    document.getElementById("status").innerText = "✅ تمت المعالجة";
  };

  setTimeout(() => mediaRecorder.stop(), 5000); // Record for 5 seconds
};

function sendReply(action) {
  const field = document.getElementById("field").value;
  const payload = {
    field,
    action
  };
  fetch("/reply", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  }).then(r => r.json()).then(res => {
    if (res.text) {
      document.getElementById("responseText").value = res.text;
    }
    document.getElementById("status").innerText = "✅ تم تحديث النص";
  });
}

function editText() {
  const edit = prompt("اكتب التعديل المطلوب:");
  if (edit) {
    sendReply("edit:" + edit);
  }
}

function generateReport() {
  fetch("/generate", { method: "POST" })
    .then(res => res.blob())
    .then(blob => {
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "police_report.docx";
      document.body.appendChild(a);
      a.click();
      a.remove();
      document.getElementById("status").innerText = "📩 تم إنشاء التقرير";
    });
}
