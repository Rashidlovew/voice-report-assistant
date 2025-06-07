let isRecording = false;
let mediaRecorder;
let audioChunks = [];
const statusText = document.getElementById("status");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");

async function startAssistant() {
    await playAudioStream("مرحباً بك، دعنا نبدأ بإنشاء التقرير خطوة بخطوة.");
    await nextPrompt();
}

async function nextPrompt() {
    const response = await fetch("/submitAudio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: null })  // kickstart if needed
    });
    const result = await response.json();
    responseText.innerText = result.response;
    await playAudioStream(result.response);
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
                body: JSON.stringify({ audio: base64Audio })
            });
            const result = await response.json();
            transcriptionText.innerText = result.transcript;
            responseText.innerText = result.response;
            await playAudioStream(result.response);
            if (result.action !== "done") startRecording();
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
    const mic = audioContext.createMediaStreamSource(stream);
    const processor = audioContext.createScriptProcessor(2048, 1, 1);
    analyser.fftSize = 2048;
    mic.connect(analyser);
    analyser.connect(processor);
    processor.connect(audioContext.destination);
    let lastSound = Date.now();
    processor.onaudioprocess = () => {
        const data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        const rms = Math.sqrt(data.reduce((a, b) => a + Math.pow((b - 128) / 128, 2), 0) / data.length);
        if (rms * 100 > threshold) lastSound = Date.now();
        if (Date.now() - lastSound > silenceDelay && isRecording) {
            onSilence();
            mic.disconnect();
            processor.disconnect();
            audioContext.close();
        }
    };
}
