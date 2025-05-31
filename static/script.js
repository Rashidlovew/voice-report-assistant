let mediaRecorder;
let audioChunks = [];
let secondRecorder;
let secondChunks = [];
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const responseAudio = document.getElementById('responseAudio');
const status = document.getElementById('status');
const fieldLabel = document.getElementById('fieldLabel');

const fields = [
    "Date",
    "Briefing",
    "LocationObservations",
    "Examination",
    "Outcomes",
    "TechincalOpinion"
];

const fieldPrompts = {
    "Date": "🎙️ أرسل تاريخ الواقعة.",
    "Briefing": "🎙️ أرسل موجز الواقعة.",
    "LocationObservations": "🎙️ أرسل معاينة الموقع حيث بمعاينة موقع الحادث تبين ما يلي .....",
    "Examination": "🎙️ أرسل نتيجة الفحص الفني ... حيث بفحص موضوع الحادث تبين ما يلي .....",
    "Outcomes": "🎙️ أرسل النتيجة حيث أنه بعد المعاينة و أجراء الفحوص الفنية اللازمة تبين ما يلي:.",
    "TechincalOpinion": "🎙️ أرسل الرأي الفني."
};

let currentStep = 0;
let fieldData = {};
let lastPreview = "";

function updateFieldLabel() {
    if (currentStep < fields.length) {
        const fieldKey = fields[currentStep];
        fieldLabel.textContent = fieldPrompts[fieldKey];
    } else {
        fieldLabel.textContent = "✅ تم الانتهاء من جميع الحقول.";
        status.textContent = "📄 جاري إعداد التقرير...";
        // Later: POST to /generate_report
    }
}

async function sendAudio(blob, route) {
    const formData = new FormData();
    formData.append('audio', blob, 'input.webm');
    const response = await fetch(route, {
        method: 'POST',
        body: formData
    });
    return await response.json();
}

function autoListenForReply() {
    status.textContent = "🎧 استمع الآن لردك...";
    secondChunks = [];
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        secondRecorder = new MediaRecorder(stream);
        secondRecorder.start();
        secondRecorder.ondataavailable = e => secondChunks.push(e.data);
        setTimeout(() => {
            secondRecorder.stop();
        }, 4000);
        secondRecorder.onstop = async () => {
            const replyBlob = new Blob(secondChunks, { type: 'audio/webm' });
            const result = await sendAudio(replyBlob, "/reply");

            if (result.action === "accept") {
                const fieldKey = fields[currentStep];
                fieldData[fieldKey] = lastPreview;
                currentStep++;
                updateFieldLabel();
            } else if (result.action === "redo") {
                status.textContent = "🔁 يرجى إعادة التسجيل لنفس الحقل...";
            } else if (result.action === "edit") {
                lastPreview = result.modified_text;
                const fieldKey = fields[currentStep];
                fieldData[fieldKey] = lastPreview;
                currentStep++;
                updateFieldLabel();
            } else {
                status.textContent = "❓ لم يتم فهم الرد.";
            }
        };
    });
}

recordBtn.onclick = async () => {
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();

    mediaRecorder.ondataavailable = e => {
        audioChunks.push(e.data);
    };

    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const fieldKey = fields[currentStep];
        const result = await sendAudio(blob, `/voice?field=${fieldKey}`);

        if (result.audio_url && result.preview) {
            responseAudio.src = result.audio_url;
            responseAudio.play();
            lastPreview = result.preview;
            status.textContent = "✅ النص المعاد صياغته: " + lastPreview;

            responseAudio.onended = () => {
                autoListenForReply();
            };
        } else {
            status.textContent = "❌ حدث خطأ";
        }
    };

    recordBtn.disabled = true;
    stopBtn.disabled = false;
    status.textContent = "🔴 جاري التسجيل...";
};

stopBtn.onclick = () => {
    mediaRecorder.stop();
    recordBtn.disabled = false;
    stopBtn.disabled = true;
    status.textContent = "⏹️ توقف التسجيل";
};

updateFieldLabel();
