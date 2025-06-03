let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startBtn");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const audioPlayer = document.getElementById("audioPlayer");

startBtn.addEventListener("click", async () => {
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
                    transcriptionText.textContent = result.transcript;
                    responseText.textContent = result.response;

                    // Play streaming audio from server
                    const audio = new Audio(`/stream-audio?text=${encodeURIComponent(result.response)}`);
                    audio.play();

                    audio.onended = () => {
                        startBtn.click();  // loop again
                    };
                } catch (err) {
                    console.error("Error:", err);
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        startBtn.textContent = "⏹️ Stop Recording";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startBtn.textContent = "🎙️ Start Talking";
        isRecording = false;
    }
});
