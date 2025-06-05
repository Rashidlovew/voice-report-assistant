// script.js (Front-end)
let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startBtn");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const micIcon = document.getElementById("micIcon");

startBtn.addEventListener("click", () => {
    startGreetingAndAssistant();
});

function showMicIcon(show) {
    micIcon.style.display = show ? "inline-block" : "none";
}

function startGreetingAndAssistant() {
    playAudioStream("مرحباً! كيف يمكنني مساعدتك اليوم؟").then(() => {
        startAssistant();
    });
}

async function playAudioStream(text) {
    return new Promise((resolve) => {
        audioPlayer.src = `/stream-audio?text=${encodeURIComponent(text)}`;
        audioPlayer.play();
        audioPlayer.addEventListener("ended", function handler() {
            audioPlayer.removeEventListener("ended", handler);
            resolve();
        });
    });
}

async function startAssistant() {
    await startRecording();

    setTimeout(() => {
        if (isRecording) {
            stopRecording();
        }
    }, 30000);
}

async function startRecording() {
    if (isRecording) return;

    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
            audioChunks.push(event.data);
        }
    };

    mediaRecorder.onstop = async () => {
        showMicIcon(false);
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
            transcriptionText.textContent = result.transcript || "";
            responseText.textContent = result.response || "";

            if (result.response) {
                await playAudioStream(result.response);
                startAssistant();
            }
        };
        reader.readAsDataURL(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;
    showMicIcon(true);
    detectSilence(stream, stopRecording, 4000, 3);
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    showMicIcon(false);
}

function detectSilence(stream, onSilence, silenceDelay = 4000, threshold = 3) {
    const audioContext = new AudioContext();
    const analyser = audioContext.createAnalyser();
    const microphone = audioContext.createMediaStreamSource(stream);
    const scriptProcessor = audioContext.createScriptProcessor(2048, 1, 1);

    analyser.smoothingTimeConstant = 0.8;
    analyser.fftSize = 2048;
    microphone.connect(analyser);
    analyser.connect(scriptProcessor);
    scriptProcessor.connect(audioContext.destination);

    let lastSoundTime = Date.now();

    scriptProcessor.onaudioprocess = function () {
        const array = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(array);
        let sum = 0;
        for (let i = 0; i < array.length; i++) {
            const value = (array[i] - 128) / 128;
            sum += value * value;
        }
        const rms = Math.sqrt(sum / array.length);
        const volume = rms * 100;

        if (volume > threshold) {
            lastSoundTime = Date.now();
        }

        if (Date.now() - lastSoundTime > silenceDelay && isRecording) {
            onSilence();
            microphone.disconnect();
            scriptProcessor.disconnect();
            audioContext.close();
        }
    };
}
