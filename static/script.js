let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let currentField = 0;

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");
const playButton = document.getElementById("play-button");

const fields = [
    "كيف حالك اليوم؟",
    "أخبرني عن تاريخ الواقعة.",
    "ما الذي لاحظته في موقع الحادث؟",
    "ما نتائج الفحص الفني؟",
    "ما النتيجة النهائية؟",
    "ما هو رأيك الفني؟"
];

function playVoice(src) {
    const audio = new Audio(src);
    audio.play().catch(err => {
        statusText.innerHTML = "❗ الصوت غير مدعوم في هذا المتصفح. جرب Chrome.";
        console.error("Audio playback failed:", err);
    });
    audio.onended = () => {
        startRecording();
    };
}

function updatePromptAndPlay() {
    const promptText = fields[currentField];
    fetch(`/fieldPrompt?text=${encodeURIComponent(promptText)}`)
        .then(res => res.json())
        .then(data => {
            statusText.innerHTML = `🧠 AI: ${data.prompt}`;
            playVoice(data.audio);
        })
        .catch(err => {
            console.error("Prompt Error:", err);
            statusText.innerText = "❌ فشل في تحميل السؤال.";
        });
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = () => {
            const audioBlob = new Blob(audioChunks);
            const reader = new FileReader();
            reader.onloadend = () => {
                const base64Audio = reader.result;

                fetch("/submitAudio", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ audio: base64Audio })
                })
                .then(res => res.json())
                .then(data => {
                    const reply = data.transcript || "لم يتم التعرف على الكلام";
                    const ai = data.response || "";
                    responseArea.value += `👤: ${reply}\n🧠: ${ai}\n\n`;
                    statusText.innerHTML = `🧠 AI: ${ai}`;
                    if (data.audio) {
                        playVoice("data:audio/mp3;base64," + data.audio);
                    }
                    currentField++;
                    if (currentField < fields.length) {
                        setTimeout(updatePromptAndPlay, 1500);
                    } else {
                        statusText.innerText = "✅ انتهت المحادثة.";
                    }
                })
                .catch(err => {
                    console.error("Submit Error:", err);
                    statusText.innerText = "❌ حدث خطأ أثناء إرسال الصوت.";
                });
            };
            reader.readAsDataURL(audioBlob);
        };

        mediaRecorder.start();
        statusText.innerText = "🎤 يتم التسجيل...";
        setTimeout(() => {
            mediaRecorder.stop();
        }, 6000); // record for 6 seconds
    }).catch(err => {
        statusText.innerText = "🚫 لم يتم السماح بالميكروفون.";
        console.error("Mic error:", err);
    });
}

startButton.addEventListener("click", () => {
    startButton.disabled = true;
    currentField = 0;
    updatePromptAndPlay();
});
