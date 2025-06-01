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
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ audio: base64Audio })
                    });

                    const result = await response.json();
                    responseArea.value = result.transcript + "\n\n" + result.response;
                    statusText.innerText = "🔊 AI: " + result.response;

                    const audio = new Audio("data:audio/mp3;base64," + result.audio);
                    audio.play();
                    audio.onerror = () => {
                        statusText.innerText += "\n❗ الصوت غير مدعوم في هذا المتصفح. جرب Chrome.";
                    };

                    audio.onended = () => startButton.click();  // Continue listening
                } catch (err) {
                    statusText.innerText = "❌ Error processing audio.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 Recording... please speak.";
        startButton.innerText = "⏹️ Stop";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ Start Talking";
        isRecording = false;
    }
});
