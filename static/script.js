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

async function startAssistant() {
    const greeting = `👋 مرحباً بك، لنبدأ إعداد التقرير. ${getPrompt(currentFieldIndex)}`;
    statusText.innerText = "🔊 يتم التشغيل...";
    await playAudioStream(greeting);
    startRecording();
}

function getPrompt(index) {
    const prompts = {
        "Date": "🎙️ أرسل تاريخ الواقعة.",
        "Briefing": "🎙️ أرسل موجز الواقعة.",
        "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
        "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
        "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
        "TechincalOpinion": "🎙️ أرسل الرأي الفني."
    };
    return prompts[fields[index]] || "";
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

            if (result.action === "redo" || result.action === "repeat") {
                startAssistant();
            } else if (result.action === "restart") {
                currentFieldIndex = 0;
                startAssistant();
            } else if (result.action === "done") {
                statusText.innerText = "✅ تم الانتهاء من التقرير";
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
