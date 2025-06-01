let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

function playAudioFromBase64(base64Data) {
    try {
        const audioElement = document.createElement("audio");
        audioElement.src = "data:audio/mpeg;base64," + base64Data;
        audioElement.type = "audio/mpeg";
        audioElement.autoplay = true;

        // Optional: fallback if audio fails
        audioElement.onerror = () => {
            statusText.innerHTML = "❗ الصوت غير مدعوم في هذا المتصفح. جرّب Chrome.";
        };

        document.body.appendChild(audioElement); // Append to trigger autoplay in some browsers
    } catch (e) {
        console.error("Failed to play audio:", e);
        statusText.innerText = "❗ حدث خطأ في تشغيل الصوت.";
    }
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
                    console.log("AI Response:", result);

                    if (result.error) {
                        statusText.innerText = "❗ " + result.error;
                        return;
                    }

                    // Show text
                    responseArea.value += `\n🧠 AI: ${result.response}`;
                    statusText.innerHTML = `🧠 AI: ${result.response}`;

                    // Play voice
                    if (result.audio) {
                        playAudioFromBase64(result.audio);
                    } else {
                        console.warn("No audio returned.");
                    }

                    // Auto-record again
                    setTimeout(() => startButton.click(), 1000);
                } catch (err) {
                    console.error("Error:", err);
                    statusText.innerText = "❌ خطأ في الاتصال بالخادم.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 جاري التسجيل...";
        startButton.innerText = "⏹️ إيقاف التسجيل";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ ابدأ المحادثة";
        isRecording = false;
    }
});
