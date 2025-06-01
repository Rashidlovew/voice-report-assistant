let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

function playAudioBase64(base64Data) {
    const audio = new Audio();
    audio.src = "data:audio/mpeg;base64," + base64Data;
    audio.play().catch(err => {
        console.error("🔴 Audio playback failed:", err);
        statusText.innerText = "❗ الصوت غير مدعوم في هذا المتصفح. جرّب Chrome.";
    });
}

startButton.addEventListener("click", async () => {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener("stop", async () => {
            const audioBlob = new Blob(audioChunks);
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Audio = reader.result;
                try {
                    const response = await fetch("/submitAudio", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ audio: base64Audio })
                    });

                    const result = await response.json();
                    responseArea.value += "\\n🧠 أنت: " + result.transcript + "\\n🤖 AI: " + result.response;
                    statusText.innerText = "🤖 AI: " + result.response;

                    playAudioBase64(result.audio);
                } catch (err) {
                    statusText.innerText = "❌ حدث خطأ أثناء المعالجة.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 جاري التسجيل... تحدث الآن.";
        startButton.innerText = "⏹️ أوقف التسجيل";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ ابدأ المحادثة";
        isRecording = false;
    }
});

window.onload = async () => {
    const response = await fetch("/fieldPrompt?text=مرحباً، كيف حالك اليوم؟");
    const result = await response.json();
    statusText.innerText = "🤖 AI: " + result.prompt;
    playAudioBase64(result.audio);
};
