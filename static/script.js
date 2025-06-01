let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

// Automatically speak welcome message on load
window.onload = async () => {
    try {
        const res = await fetch("/fieldPrompt?text=مرحباً، كيف حالك اليوم؟");
        const data = await res.json();
        statusText.innerText = "🤖 AI: " + data.prompt;
        const audio = new Audio(data.audio);
        audio.play();

        audio.onended = () => {
            startButton.click(); // Start recording after greeting
        };
    } catch (err) {
        statusText.innerText = "❌ Failed to load welcome message.";
    }
};

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
                    responseArea.value += "👤 أنت: " + result.transcript + "\n\n";
                    responseArea.value += "🤖 AI: " + result.response + "\n\n";
                    statusText.innerText = "🤖 AI: " + result.response;

                    const audio = new Audio("data:audio/mp3;base64," + result.audio);
                    audio.play();

                    // Auto-record after voice reply finishes
                    audio.onended = () => startButton.click();
                } catch (err) {
                    statusText.innerText = "❌ Error processing audio.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 Listening... please speak.";
        startButton.innerText = "⏹️ Stop";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ Start Talking";
        isRecording = false;
    }
});
