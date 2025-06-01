let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("startButton");
const responseBox = document.getElementById("response");

startButton.onclick = async () => {
    startButton.disabled = true;
    responseBox.innerText = "🎤 استعد للتسجيل...";

    await fetch("/start", { method: "POST" });
    await getPromptAndStartRecording();
};

async function getPromptAndStartRecording() {
    const res = await fetch("/fieldPrompt");
    const { text, audio, done } = await res.json();

    responseBox.innerText = text || "🤖";

    if (audio) {
        const audioElement = new Audio("data:audio/mp3;base64," + audio);
        audioElement.play();
        audioElement.onended = () => startRecording();
    } else {
        startRecording();
    }
}

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
            audioChunks.push(e.data);
        }
    };

    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const base64Audio = await blobToBase64(blob);

        const response = await fetch("/submitAudio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio: base64Audio })
        });

        const result = await response.json();
        responseBox.innerText = result.text || "🤖";

        if (!result.done) {
            await getPromptAndStartRecording();
        } else {
            responseBox.innerText += "\n✅ تم الانتهاء من جميع الخطوات.";
            startButton.disabled = false;
        }
    };

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000);
}

function blobToBase64(blob) {
    return new Promise((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
    });
}
