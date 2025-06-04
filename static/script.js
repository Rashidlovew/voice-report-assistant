let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let audioContext;
let analyser;
let sourceNode;
let silenceTimer;
let recordingStartTime;
let micStream;
let preMicStarted = false;

const startBtn = document.getElementById("startBtn");
const statusText = document.getElementById("statusText");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const audioPlayer = document.getElementById("audioPlayer");

startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    statusText.textContent = "🎤 Listening...";
    console.log("🎤 Assistant started");
    await speakText("مرحباً! كيف يمكنني مساعدتك اليوم؟");
    startAssistant();
});

function startAssistant() {
    console.log("🎙️ Starting mic...");
    startRecording();
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        audioContext = new AudioContext();
        const source = audioContext.createMediaStreamSource(stream);
        detectSilence(() => {
            console.log("🤫 Silence detected");
            stopRecording();
        }, 0.005);

        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.ondataavailable = event => {
            audioChunks.push(event.data);
        };

        mediaRecorder.onstop = async () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const reader = new FileReader();
            reader.readAsDataURL(audioBlob);
            reader.onloadend = async () => {
                const base64Audio = reader.result;

                const response = await fetch("/submitAudio", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ audio: base64Audio })
                });

                const data = await response.json();
                transcriptionText.textContent = data.transcript;
                responseText.textContent = data.response;

                await speakText(data.response);
                startAssistant();
            };
        };

        mediaRecorder.start();
        isRecording = true;

        setTimeout(() => {
            if (isRecording) {
                console.log("⚠️ Force stop after 30s timeout.");
                stopRecording();
            }
        }, 30000);
    });
}

function stopRecording() {
    if (mediaRecorder && isRecording) {
        mediaRecorder.stop();
        isRecording = false;
    }
    if (audioContext) {
        audioContext.close();
    }
}

function detectSilence(onSilence, threshold = 0.005, timeout = 1500) {
    const analyser = audioContext.createAnalyser();
    const source = audioContext.createMediaStreamSource(mediaRecorder.stream);
    source.connect(analyser);
    analyser.fftSize = 512;
    const data = new Uint8Array(analyser.fftSize);

    function checkSilence() {
        analyser.getByteFrequencyData(data);
        const average = data.reduce((a, b) => a + b) / data.length;
        if (average < threshold * 256) {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(onSilence, timeout);
        } else {
            clearTimeout(silenceTimer);
            silenceTimer = setTimeout(checkSilence, timeout);
        }
    }

    checkSilence();
}

async function speakText(text) {
    return new Promise((resolve) => {
        const streamUrl = `/stream-audio?text=${encodeURIComponent(text)}`;
        const mediaSource = new MediaSource();
        audioPlayer.src = URL.createObjectURL(mediaSource);

        mediaSource.addEventListener("sourceopen", () => {
            const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
            fetch(streamUrl).then(res => {
                const reader = res.body.getReader();
                const queue = [];
                let isAppending = false;

                const pump = () => {
                    reader.read().then(({ done, value }) => {
                        if (done) {
                            if (!isAppending) mediaSource.endOfStream();
                            return;
                        }
                        queue.push(value);
                        tryAppend();
                        pump();
                    });
                };

                const tryAppend = () => {
                    if (isAppending || queue.length === 0 || sourceBuffer.updating) return;
                    isAppending = true;
                    const chunk = queue.shift();
                    sourceBuffer.appendBuffer(chunk);
                };

                sourceBuffer.addEventListener("updateend", () => {
                    isAppending = false;
                    tryAppend();
                });

                pump();
            });
        });

        audioPlayer.onended = () => {
            console.log("✅ Greeting finished, starting to record...");
            setTimeout(() => resolve(), 500);
        };

        audioPlayer.play().catch(e => {
            console.warn("Playback failed:", e);
            resolve();
        });
    });
}
