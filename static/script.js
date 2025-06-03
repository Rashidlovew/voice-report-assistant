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

                    if (result.error) {
                        transcriptionText.textContent = "❌ Error: " + result.error;
                        return;
                    }

                    transcriptionText.textContent = result.transcript;
                    responseText.textContent = result.response;

                    // 🔊 Live streaming audio using MediaSource
                    const streamUrl = `/stream-audio?text=${encodeURIComponent(result.response)}`;
                    const mediaSource = new MediaSource();
                    audioPlayer.src = URL.createObjectURL(mediaSource);

                    mediaSource.addEventListener("sourceopen", () => {
                        const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
                        fetch(streamUrl)
                            .then(res => {
                                const reader = res.body.getReader();
                                const pump = () => reader.read().then(({ done, value }) => {
                                    if (done) {
                                        mediaSource.endOfStream();
                                        return;
                                    }
                                    sourceBuffer.appendBuffer(value);
                                    pump();
                                });
                                pump();
                            });
                    });

                    audioPlayer.play();
                    audioPlayer.onended = () => {
                        startBtn.click(); // 🔁 auto start next round
                    };

                } catch (err) {
                    console.error("❌ Audio send error:", err);
                    transcriptionText.textContent = "❌ Error sending audio.";
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
