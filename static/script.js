// script.js

let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let audioContext;
let silenceTimer;

const startBtn = document.getElementById("startBtn");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const audioPlayer = document.getElementById("audioPlayer");

startBtn.addEventListener("click", startConversation);

async function startConversation() {
    await speakAndListen("مرحباً! كيف يمكنني مساعدتك اليوم؟");
}

async function speakAndListen(promptText) {
    await speakText(promptText);
    startRecording();
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        detectSilence(() => {
            console.log("🤫 Silence detected");
            stopRecording();
        }, 0.005); // More sensitive silence detection

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = reader.result;

                const response = await fetch("/submitAudio", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ audio: base64Audio })
                });

                const data = await response.json();
                transcriptionText.textContent = data.transcript;
                responseText.textContent = data.response;
                playAudioStream(data.response);
            };
        };

        mediaRecorder.start();
        isRecording = true;

        // Safety net timeout (30s)
        setTimeout(() => {
            if (isRecording) {
                console.log("⚠️ Force stop after 30s timeout.");
                stopRecording();
            }
        }, 30000);
    });
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
    }
    if (audioContext) {
        audioContext.close();
    }
}

function detectSilence(onSilence, threshold = 0.005, timeout = 1500) {
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(mediaRecorder.stream);
    source.connect(analyser);
    analyser.fftSize = 512;
    const data = new Uint8Array(analyser.fftSize);

    function checkSilence() {
        analyser.getByteFrequencyData(data);
        const average = data.reduce((a, b) => a + b) / data.length;
        if (average < threshold * 256) {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(onSilence, timeout);
        } else {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(checkSilence, timeout);
        }
    }

    checkSilence();
}

function playAudioStream(text) {
    const audio = new Audio(`/stream-audio?text=${encodeURIComponent(text)}`);
    audioPlayer.src = audio.src;
    audio.play();
    audio.onended = () => {
        startRecording();
    };
}
