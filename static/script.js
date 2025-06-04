let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startBtn");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");

startBtn.addEventListener("click", () => {
    startGreetingAndAssistant();
});

function startGreetingAndAssistant() {
    console.log("🔊 Playing greeting...");
    playAudioStream("مرحباً! كيف يمكنني مساعدتك اليوم؟").then(() => {
        console.log("✅ Greeting finished. Starting assistant...");
        startAssistant();
    });
}

async function playAudioStream(text) {
    return new Promise((resolve) => {
        audioPlayer.src = `/stream-audio?text=${encodeURIComponent(text)}`;
        audioPlayer.play();

        // Use event listener to detect end of audio
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
            console.warn("⚠️ Force stop after 30s timeout.");
            stopRecording();
        }
    }, 30000); // Auto stop after 30 seconds
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
                startAssistant(); // Loop again
            }
        };
        reader.readAsDataURL(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;
    console.log("🎙️ Recording started...");

    // Auto stop when silence is detected (optional upgrade)
    detectSilence(stream, stopRecording);
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    console.log("🛑 Recording stopped.");
}

function detectSilence(stream, onSilence, silenceDelay = 2000, threshold = -50) {
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
        const array = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(array);
        const volume = array.reduce((a, b) => a + b) / array.length;

        if (volume > threshold) {
            lastSoundTime = Date.now();
        }

        if (Date.now() - lastSoundTime > silenceDelay && isRecording) {
            console.log("🤫 Silence detected. Stopping...");
            onSilence();
            microphone.disconnect();
            scriptProcessor.disconnect();
            audioContext.close();
        }
    };
}
