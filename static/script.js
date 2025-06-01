let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

async function getNextPrompt() {
    const res = await fetch("/fieldPrompt");
    const data = await res.json();
    statusText.innerHTML = `🧠 AI: ${data.prompt} <button onclick="playVoice('${data.audio}')">🔊</button>`;
    playVoice(data.audio);
}

function playVoice(src) {
    const audio = new Audio(src);
    audio.play();
    audio.onended = () => startRecording();
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const blob = new Blob(audioChunks, { type: "audio/webm" });
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Audio = reader.result;

                const res = await fetch("/submitAudio", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ audio: base64Audio })
                });

                const result = await res.json();
                responseArea.value += `👤 ${result.transcript}\n🤖 ${result.response}\n\n`;

                getNextPrompt();
            };
            reader.readAsDataURL(blob);
        };

        mediaRecorder.start();
        setTimeout(() => {
            mediaRecorder.stop();
        }, 5000); // 5 sec per response
    });
}

startButton.addEventListener("click", () => {
    startButton.disabled = true;
    getNextPrompt(); // start the voice conversation
});
