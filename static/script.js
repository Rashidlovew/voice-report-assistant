const startBtn = document.getElementById("startBtn");
const statusDiv = document.getElementById("status");
const responseDiv = document.getElementById("response");

let mediaRecorder;
let chunks = [];
let isRecording = false;

startBtn.addEventListener("click", async () => {
    if (isRecording) return;
    statusDiv.innerText = "🎙️ تسجيل الصوت...";
    responseDiv.innerText = "";
    isRecording = true;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    chunks = [];

    mediaRecorder.ondataavailable = (e) => chunks.push(e.data);
    mediaRecorder.onstop = async () => {
        const blob = new Blob(chunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.readAsDataURL(blob);
        reader.onloadend = async () => {
            const base64Audio = reader.result;
            const res = await fetch("/submitAudio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ audio: base64Audio })
            });
            const data = await res.json();
            statusDiv.innerText = "✅ تم التحليل";
            responseDiv.innerText = `📝 النص المعاد صياغته: ${data.response}`;

            // تشغيل الرد الصوتي
            const audioRes = await fetch(`/stream-audio?text=${encodeURIComponent(data.response)}`);
            const audioBlob = await audioRes.blob();
            const audioUrl = URL.createObjectURL(audioBlob);
            const audio = new Audio(audioUrl);
            audio.play();
        };
    };

    mediaRecorder.start();

    setTimeout(() => {
        if (isRecording) {
            mediaRecorder.stop();
            isRecording = false;
            statusDiv.innerText = "⏹️ تم إنهاء التسجيل.";
        }
    }, 6000); // 6 ثواني حد أقصى للتسجيل
});