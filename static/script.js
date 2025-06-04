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
            resolve();
        };

        audioPlayer.play().catch(e => {
            console.warn("Playback failed:", e);
            resolve();
        });
    });
}

// (rest of your code continues...)
