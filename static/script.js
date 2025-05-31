let mediaRecorder;
let audioChunks = [];
const recordBtn = document.getElementById('recordBtn');
const stopBtn = document.getElementById('stopBtn');
const responseAudio = document.getElementById('responseAudio');
const status = document.getElementById('status');
const fieldLabel = document.getElementById('fieldLabel');

const fields = [
    "التاريخ",
    "مكان المعاينة",
    "ملاحظات الفحص",
    "الإجراءات",
    "النتائج",
    "الرأي الفني"
];

let currentStep = 0;
let fieldData = {};

function updateFieldLabel() {
    if (currentStep < fields.length) {
        fieldLabel.textContent = `أدخل ${fields[currentStep]} بالصوت`;
    } else {
        fieldLabel.textContent = "✅ تم الانتهاء من جميع الحقول";
        status.textContent = "تم جمع كل البيانات بنجاح.";
    }
}

recordBtn.onclick = async () => {
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    mediaRecorder.start();

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const formData = new FormData();
        formData.append('audio', audioBlob, 'input.webm');

        status.textContent = "⏳ جاري المعالجة...";
        try {
            const response = await fetch('/voice', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error("Failed to get response from server.");
            }

            const audio = await response.blob();
            responseAudio.src = URL.createObjectURL(audio);
            responseAudio.play();

            // Save step
            fieldData[fields[currentStep]] = "تم إدخال هذا الحقل.";
            currentStep++;
            updateFieldLabel();
        } catch (error) {
            status.textContent = "❌ حدث خطأ أثناء إرسال الصوت.";
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
    status.textContent = "⏹️ توقف التسجيل، جاري الإرسال...";
};

updateFieldLabel();
