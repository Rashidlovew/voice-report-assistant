let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

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
                        statusText.innerHTML = `❌ Error: ${result.error}`;
                        return;
                    }

                    responseArea.value += `\n🧑‍💼 أنت: ${result.transcript}\n🤖 AI: ${result.response}\n`;
                    statusText.innerHTML = `🤖 AI: ${result.response}`;

                    const audio = new Audio("data:audio/mp3;base64," + result.audio);
                    audio.play();

                    audio.onended = () => {
                        startButton.click(); // Auto-listen again
                    };
                } catch (err) {
                    statusText.innerHTML = "❌ Error sending audio.";
                }
            };

            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 Listening... please speak";
        startButton.innerText = "⏹️ Stop";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ Start Talking";
        isRecording = false;
    }
});

// Auto greet user
window.addEventListener("DOMContentLoaded", async () => {
    try {
        const greeting = "مرحباً، كيف حالك اليوم؟";
        const response = await fetch(`/fieldPrompt?text=${encodeURIComponent(greeting)}`);
        const result = await response.json();

        statusText.innerHTML = `🤖 AI: ${result.prompt}`;
        const audio = new Audio(result.audio);
        audio.play();
    } catch (err) {
        statusText.innerHTML = "❗ الصوت غير مدعوم في هذا المتصفح. جرّب Chrome.";
    }
});
