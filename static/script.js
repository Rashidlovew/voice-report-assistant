let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let audioStream;
const statusText = document.getElementById("status");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");

let silenceTimeoutTriggered = false;

async function startAssistant() {
    statusText.innerText = "🎧 المساعد جاهز...";
    const response = await fetch("/submitAudio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: null })
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
    audioStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(audioStream);
    audioChunks = [];

    mediaRecorder.ondataavailable = e => audioChunks.push(e.data);
    mediaRecorder.onstop = async () => {
        if (silenceTimeoutTriggered) {
            silenceTimeoutTriggered = false;
            await playAudioStream("هل تود إضافة شيء آخر؟ إذا نعم، تفضل بالتحدث. وإذا لا، فقط قل تم.");
            startRecording();
            return;
        }

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
            if (result.action !== "done") {
                startRecording();
            } else {
                statusText.innerText = "✅ تم الانتهاء من إعداد التقرير.";
            }
        };
        reader.readAsDataURL(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;
    statusText.innerText = "🎤 جاري الاستماع...";
    detectSilence(audioStream, stopRecording, 3000, 5);  // ⏱️ مهلة صمت = 3 ثواني
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    if (audioStream) {
        audioStream.getTracks().forEach(track => track.stop());
    }
    statusText.innerText = "⏸️ توقف التسجيل مؤقتاً.";
}

function detectSilence(stream, onSilence, silenceDelay = 3000, threshold = 5) {
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    const mic = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(2048, 1, 1);
    analyser.fftSize = 2048;
    mic.connect(analyser);
    analyser.connect(processor);
    processor.connect(context.destination);

    let lastSound = Date.now();
    processor.onaudioprocess = () => {
        const data = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(data);
        const rms = Math.sqrt(data.reduce((a, b) => a + Math.pow((b - 128) / 128, 2), 0) / data.length);
        if (rms * 100 > threshold) lastSound = Date.now();
        if (Date.now() - lastSound > silenceDelay && isRecording) {
            silenceTimeoutTriggered = true;
            onSilence();
            mic.disconnect();
            processor.disconnect();
            context.close();
        }
    };
}
