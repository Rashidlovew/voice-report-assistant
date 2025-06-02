let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

// ✅ Convert base64 → binary → playable audio
function playAudioFromBase64(base64Audio) {
    const byteCharacters = atob(base64Audio);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'audio/mpeg' });
    const audioUrl = URL.createObjectURL(blob);

    const audio = new Audio(audioUrl);
    audio.play().catch(err => console.error("🔴 Audio play error:", err));

    audio.onended = () => {
        setTimeout(() => startButton.click(), 300);
    };
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

                    if (result.error) {
                        statusText.innerText = "❌ Error: " + result.error;
                        return;
                    }

                    responseArea.value += `\n👤 أنت: ${result.transcript}\n🤖 AI: ${result.response}\n`;
                    statusText.innerText = "🤖 AI: " + result.response;

                    playAudioFromBase64(result.audio);
                } catch (err) {
                    console.error("❌ Error sending audio:", err);
                    statusText.innerText = "❌ Failed to process your audio.";
                }
            };

            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 جاري التسجيل... تفضل بالكلام.";
        startButton.innerText = "⏹️ إيقاف التسجيل";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ ابدأ الحديث";
        isRecording = false;
    }
});
