let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let currentFieldIndex = 0;

const startBtn = document.getElementById("startBtn");
const audioPlayer = document.getElementById("audioPlayer");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const micIcon = document.getElementById("micIcon");
const fieldButtons = document.getElementById("fieldButtons");

const fields = [
    "Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"
];

startBtn.addEventListener("click", () => {
    startConversation();
});

function showMicIcon(show) {
    micIcon.style.display = show ? "inline-block" : "none";
}

function showFieldButtons() {
    fieldButtons.innerHTML = '';
    fields.forEach((field, index) => {
        const btn = document.createElement("button");
        btn.textContent = `تعديل ${getFieldLabel(field)}`;
        btn.onclick = () => {
            currentFieldIndex = index;
            askField(field);
        };
        fieldButtons.appendChild(btn);
    });
}

function getFieldLabel(field) {
    const labels = {
        Date: "التاريخ",
        Briefing: "موجز الواقعة",
        LocationObservations: "معاينة الموقع",
        Examination: "نتيجة الفحص",
        Outcomes: "النتيجة",
        TechincalOpinion: "الرأي الفني"
    };
    return labels[field] || field;
}

async function startConversation() {
    await playAudioStream("مرحباً! كيف يمكنني مساعدتك اليوم؟");
    askField(fields[currentFieldIndex]);
}

async function askField(fieldKey) {
    await playAudioStream(getPrompt(fieldKey));
    await startRecording();
}

function getPrompt(field) {
    const prompts = {
        Date: "🎙️ من فضلك، ما هو تاريخ الواقعة؟",
        Briefing: "🎙️ من فضلك، أرسل موجزاً رسمياً للواقعة.",
        LocationObservations: "🎙️ من فضلك، صف ملاحظاتك أثناء معاينة الموقع.",
        Examination: "🎙️ ما هي نتيجة الفحص الفني؟",
        Outcomes: "🎙️ ما النتيجة بعد الفحص والمعاينة؟",
        TechincalOpinion: "🎙️ ما هو رأيك الفني النهائي؟"
    };
    return prompts[field];
}

async function playAudioStream(text) {
    return new Promise((resolve) => {
        audioPlayer.src = `/stream-audio?text=${encodeURIComponent(text)}`;
        audioPlayer.play();
        audioPlayer.onended = resolve;
    });
}

async function startRecording() {
    if (isRecording) return;
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];
    mediaRecorder.ondataavailable = e => {
        if (e.data.size > 0) audioChunks.push(e.data);
    };
    mediaRecorder.onstop = async () => {
        showMicIcon(false);
        const blob = new Blob(audioChunks, { type: "audio/webm" });
        const reader = new FileReader();
        reader.onloadend = async () => {
            const base64Audio = reader.result;
            const res = await fetch("/submitAudio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ audio: base64Audio, field: fields[currentFieldIndex] })
            });
            const data = await res.json();
            transcriptionText.textContent = data.transcript || "";
            responseText.textContent = data.response || "";

            await playAudioStream(data.response || "");

            if (data.nextStep === "continue") {
                currentFieldIndex++;
                if (currentFieldIndex < fields.length) {
                    askField(fields[currentFieldIndex]);
                } else {
                    await playAudioStream("🎉 تم استلام جميع المعلومات. سيتم إرسال التقرير بالبريد الإلكتروني.");
                    showFieldButtons();
                }
            } else if (data.nextStep === "repeat") {
                askField(fields[currentFieldIndex]);
            }
        };
        reader.readAsDataURL(blob);
    };

    mediaRecorder.start();
    isRecording = true;
    showMicIcon(true);
    detectSilence(stream, stopRecording, 6000, 5);
}

function stopRecording() {
    if (!isRecording) return;
    isRecording = false;
    mediaRecorder.stop();
    showMicIcon(false);
}

function detectSilence(stream, onSilence, silenceDelay = 6000, threshold = 5) {
    const context = new AudioContext();
    const source = context.createMediaStreamSource(stream);
    const analyser = context.createAnalyser();
    const processor = context.createScriptProcessor(2048, 1, 1);

    analyser.fftSize = 2048;
    analyser.smoothingTimeConstant = 0.8;

    source.connect(analyser);
    analyser.connect(processor);
    processor.connect(context.destination);

    let lastSound = Date.now();

    processor.onaudioprocess = () => {
        const buffer = new Uint8Array(analyser.fftSize);
        analyser.getByteTimeDomainData(buffer);
        let sum = 0;
        for (let i = 0; i < buffer.length; i++) {
            const v = (buffer[i] - 128) / 128;
            sum += v * v;
        }
        const rms = Math.sqrt(sum / buffer.length);
        const volume = rms * 100;

        if (volume > threshold) lastSound = Date.now();

        if (Date.now() - lastSound > silenceDelay && isRecording) {
            onSilence();
            source.disconnect();
            processor.disconnect();
            context.close();
        }
    };
}
