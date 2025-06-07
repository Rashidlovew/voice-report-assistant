
let isRecording = false;
let mediaRecorder;
let audioChunks = [];
const statusText = document.getElementById("status");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const fieldButtons = document.getElementById("fieldButtons");

const fields = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"];
let currentFieldIndex = 0;

function startAssistant() {
    statusText.innerText = "🎙️ جاري الاستماع...";
    startRecording();
}

async function playAudioStream(text) {
    return new Promise((resolve, reject) => {
        audioPlayer.src = `/stream-audio?text=${encodeURIComponent(text)}`;
        audioPlayer.style.display = "block";
        audioPlayer.play();
        audioPlayer.onended = () => resolve();
        audioPlayer.onerror = (err) => reject(err);
    });
}

async function startRecording() {
    if (isRecording) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => e.data.size && audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = async () => {
            const base64Audio = reader.result;
            const response = await fetch("/submitAudio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ audio: base64Audio, currentField: fields[currentFieldIndex] })
            });
            const result = await response.json();
            transcriptionText.innerText = result.transcript;
            responseText.innerText = result.response;
            await playAudioStream(result.response);
            if (result.action === "repeat") {
                startAssistant();
            } else if (result.action === "redo") {
                startAssistant();
            } else {
                currentFieldIndex++;
                if (currentFieldIndex < fields.length) {
                    startAssistant();
                } else {
                    statusText.innerText = "✅ تم الانتهاء من التقرير";
                }
            }
        };
        reader.readAsDataURL(audioBlob);
    };
    mediaRecorder.start();
    isRecording = true;
    statusText.innerText = "🎤 تسجيل...";

    detectSilence(stream, stopRecording, 6000, 5);
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    statusText.innerText = "🛑 توقف التسجيل";
}

function detectSilence(stream, onSilence, silenceDelay = 6000, threshold = 5) {
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
    scriptProcessor.onaudioprocess = () => {
        const array = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(array);
        const sum = array.reduce((acc, val) => acc + Math.pow((val - 128) / 128, 2), 0);
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

function renderFieldButtons() {
    fields.forEach(field => {
        const btn = document.createElement("button");
        btn.innerText = `🔁 أعد ${field}`;
        btn.onclick = () => {
            currentFieldIndex = fields.indexOf(field);
            startAssistant();
        };
        fieldButtons.appendChild(btn);
    });
}

window.onload = () => {
    statusText.innerText = "✅ جاهز";
    renderFieldButtons();
};
