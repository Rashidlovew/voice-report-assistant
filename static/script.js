let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let currentField = "";
let fieldQueue = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"];
let fieldIndex = 0;

const startBtn = document.getElementById("startBtn");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const micIcon = document.getElementById("micIcon");
const fieldButtons = document.getElementById("fieldButtons");
const statusDiv = document.createElement("div");
statusDiv.style.marginTop = "10px";
document.body.insertBefore(statusDiv, fieldButtons);

startBtn.addEventListener("click", () => {
    greetUser();
});

function greetUser() {
    const welcome = "مرحباً بك في مساعد التقارير الصوتي الخاص بقسم الهندسة الجنائية. سأطرح عليك مجموعة من الأسئلة الصوتية لجمع البيانات، من فضلك أجب بعد سماع كل سؤال.";
    playAudioStream(welcome).then(() => {
        fieldIndex = 0;
        startAssistant();
    });
}

function updateStatus(text) {
    statusDiv.textContent = text;
}

function showMicIcon(show) {
    micIcon.style.display = show ? "inline-block" : "none";
}

async function playAudioStream(text) {
    return new Promise((resolve) => {
        updateStatus("🔊 يتحدث.");
        audioPlayer.src = `/stream-audio?text=${encodeURIComponent(text)}`;
        audioPlayer.play();
        audioPlayer.addEventListener("ended", function handler() {
            audioPlayer.removeEventListener("ended", handler);
            updateStatus("🎤 في انتظار الصوت.");
            resolve();
        });
    });
}

async function startAssistant() {
    currentField = fieldQueue[fieldIndex];
    const arabicLabel = document.querySelector(`#fieldButtons button[data-field='${currentField}']`)?.textContent || "";
    const promptText = `🎙️ أرسل ${arabicLabel} من فضلك.`;
    await playAudioStream(promptText);
    await startRecording();

    setTimeout(() => {
        if (isRecording) stopRecording();
    }, 30000);
}

async function startRecording() {
    if (isRecording) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        showMicIcon(false);
        updateStatus("🔁 معالجة...");

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

            const intentResponse = await fetch("/analyze-intent", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: result.transcript })
            });
            const intentResult = await intentResponse.json();

            if (intentResult.intent === "approve") {
                fieldIndex++;
            } else if (intentResult.intent === "redo") {
                // stay on same field
            } else if (intentResult.intent === "restart") {
                fieldIndex = 0;
            } else if (intentResult.intent === "fieldCorrection") {
                const target = fieldQueue.indexOf(intentResult.field);
                if (target !== -1) fieldIndex = target;
            }

            if (fieldIndex < fieldQueue.length) {
                startAssistant();
            } else {
                updateStatus("✅ تم الانتهاء من جميع المدخلات.");
                playAudioStream("✅ تم الانتهاء من جميع المدخلات. شكراً لك!");
            }
        };
        reader.readAsDataURL(audioBlob);
    };

    mediaRecorder.start();
    isRecording = true;
    showMicIcon(true);
    updateStatus("🎙️ تسجيل الصوت.");
    detectSilence(stream, stopRecording, 6000, 5);
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    showMicIcon(false);
    updateStatus("🛑 تم إيقاف التسجيل");
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
        if (volume > threshold) lastSoundTime = Date.now();
        if (Date.now() - lastSoundTime > silenceDelay && isRecording) {
            onSilence();
            microphone.disconnect();
            scriptProcessor.disconnect();
            audioContext.close();
        }
    };
}

function renderFieldButtons() {
    fieldButtons.innerHTML = "";
    const arabicLabels = {
        Date: "التاريخ",
        Briefing: "موجز الواقعة",
        LocationObservations: "معاينة الموقع",
        Examination: "نتيجة الفحص الفني",
        Outcomes: "النتيجة",
        TechincalOpinion: "الرأي الفني"
    };
    fieldQueue.forEach(field => {
        const btn = document.createElement("button");
        btn.textContent = arabicLabels[field];
        btn.className = "field-btn";
        btn.setAttribute("data-field", field);
        btn.onclick = () => {
            const target = fieldQueue.indexOf(field);
            if (target !== -1) {
                fieldIndex = target;
                startAssistant();
            }
        };
        fieldButtons.appendChild(btn);
    });
}
renderFieldButtons();
