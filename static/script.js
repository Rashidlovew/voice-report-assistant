let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

startButton.addEventListener("click", async () => {
    if (!isRecording) {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener("stop", async () => {
            const audioBlob = new Blob(audioChunks);
            const reader = new FileReader();
            reader.onloadend = async () => {
                const base64Audio = reader.result;
                try {
                    const response = await fetch("/submitAudio", {
                        method: "POST",
                        headers: { "Content-Type": "application/json" },
                        body: JSON.stringify({ audio: base64Audio })
                    });
                    const result = await response.json();

                    if (result.error) {
                        statusText.innerText = "❌ خطأ: " + result.error;
                        return;
                    }

                    responseArea.value = "🗣️ " + result.transcript + "\n\n🤖 " + result.response;
                    statusText.innerText = "🔊 AI: " + result.response;

                    const audio = new Audio("data:audio/mp3;base64," + result.audio);
                    audio.play();

                    audio.onended = () => startButton.click();
                } catch (err) {
                    statusText.innerText = "❌ خطأ في معالجة الصوت.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 تسجيل... تفضل بالكلام.";
        startButton.innerText = "⏹️ إيقاف";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ ابدأ المحادثة";
        isRecording = false;
    }
});
