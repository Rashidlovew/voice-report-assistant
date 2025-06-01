const startButton = document.getElementById("startButton");
const statusDiv = document.getElementById("status");
const transcriptBox = document.getElementById("transcript");

let mediaRecorder;
let audioChunks = [];

startButton.onclick = async () => {
    if (!navigator.mediaDevices) {
        statusDiv.innerText = "🎙️ المتصفح لا يدعم تسجيل الصوت.";
        return;
    }

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
            const base64Audio = reader.result;

            const response = await fetch("/submitAudio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ audio: base64Audio })
            });

            const result = await response.json();
            transcriptBox.value = result.transcript || "لم يتم الحصول على الرد.";
        };
        reader.readAsDataURL(audioBlob);
    };

    mediaRecorder.start();
    statusDiv.innerText = "🎤 جاري الاستماع... اضغط مرة أخرى للإيقاف.";

    startButton.onclick = () => {
        mediaRecorder.stop();
        stream.getTracks().forEach(track => track.stop());
        statusDiv.innerText = "⏳ جارٍ المعالجة...";
    };
};
