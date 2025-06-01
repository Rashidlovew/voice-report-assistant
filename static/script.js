let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");
const audioPlayer = document.getElementById("audioPlayer");
const audioContainer = document.getElementById("audioContainer");

startButton.addEventListener("click", async () => {
    if (!isRecording) {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.addEventListener("dataavailable", event => {
                audioChunks.push(event.data);
            });

            mediaRecorder.addEventListener("stop", async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
                const reader = new FileReader();
                reader.onloadend = async () => {
                    const base64Audio = reader.result;
                    try {
                        const response = await fetch("/submitAudio", {
                            method: "POST",
                            headers: {
                                "Content-Type": "application/json"
                            },
                            body: JSON.stringify({ audio: base64Audio })
                        });

                        const result = await response.json();

                        const aiText = result.response || "❌ لم يتم الحصول على رد.";
                        const fullResponse = `AI 🤖: ${aiText}`;
                        statusText.innerText = fullResponse;
                        responseArea.value += "\n\n" + fullResponse;

                        if (result.audio) {
                            audioContainer.style.display = "inline-block";
                            audioPlayer.src = "data:audio/mp3;base64," + result.audio;
                            try {
                                await audioPlayer.play();
                            } catch (e) {
                                console.error("⚠️ Failed to play audio:", e);
                                statusText.innerText += "\n❗ الصوت غير مدعوم في هذا المتصفح. جرّب Chrome.";
                            }
                            audioPlayer.onended = () => startButton.click();
                        } else {
                            statusText.innerText += "\n❗ لم يتم العثور على ملف صوتي.";
                        }

                    } catch (err) {
                        statusText.innerText = "❌ حدث خطأ أثناء إرسال الصوت.";
                        console.error(err);
                    }
                };
                reader.readAsDataURL(audioBlob);
            });

            mediaRecorder.start();
            statusText.innerText = "🎙️ جاري التسجيل... تحدث الآن.";
            startButton.innerText = "⏹️ إيقاف التسجيل";
            isRecording = true;
        } catch (err) {
            statusText.innerText = "⚠️ لم يتم السماح باستخدام الميكروفون.";
            console.error(err);
        }
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎤 ابدأ المحادثة";
        isRecording = false;
    }
});

window.addEventListener("load", async () => {
    const greeting = "مرحباً، كيف حالك اليوم؟";
    try {
        const response = await fetch("/fieldPrompt?text=" + encodeURIComponent(greeting));
        const result = await response.json();
        statusText.innerText = `AI 🤖: ${result.prompt}`;
        audioContainer.style.display = "inline-block";
        audioPlayer.src = result.audio;
        await audioPlayer.play();
    } catch (err) {
        console.error("Failed to play greeting:", err);
    }
});
