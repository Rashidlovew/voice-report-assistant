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
    startAssistant();
});

async function prepareMic() {
    if (!micStream) {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }
}

async function startAssistant() {
    if (!micStream) {
        micStream = await navigator.mediaDevices.getUserMedia({ audio: true });
    }

    audioContext = new AudioContext();
    sourceNode = audioContext.createMediaStreamSource(micStream);
    analyser = audioContext.createAnalyser();
    sourceNode.connect(analyser);

    mediaRecorder = new MediaRecorder(micStream);
    audioChunks = [];

    mediaRecorder.addEventListener("dataavailable", event => {
        audioChunks.push(event.data);
    });

    mediaRecorder.addEventListener("stop", () => {
        stopSilenceDetection();
        processAudio(new Blob(audioChunks));
    });

    mediaRecorder.start();
    isRecording = true;
    recordingStartTime = performance.now();
    detectSilence(() => {
        const elapsed = performance.now() - recordingStartTime;
        if (isRecording && elapsed > 1500) {
            console.log("🛑 Silence detected, stopping recording");
            mediaRecorder.stop();
            isRecording = false;
        }
    });
}

function detectSilence(onSilence, threshold = 0.01, timeout = 1500) {
    const buffer = new Uint8Array(analyser.fftSize);
    let silenceStart = performance.now();

    function checkSilence() {
        analyser.getByteFrequencyData(buffer);
        const averageVolume = buffer.reduce((a, b) => a + b, 0) / buffer.length;
        const isSilent = averageVolume < threshold * 256;

        console.log("🔊 Avg Volume:", averageVolume.toFixed(2), isSilent ? "(silent)" : "(speaking)");

        if (isSilent) {
            if (performance.now() - silenceStart > timeout) {
                console.log("🛑 Silence threshold reached.");
                onSilence();
                return;
            }
        } else {
            silenceStart = performance.now();
        }

        silenceTimer = requestAnimationFrame(checkSilence);
    }

    setTimeout(() => {
        if (isRecording) {
            console.log("⚠️ Force stop after 7s timeout.");
            onSilence();
        }
    }, 7000);

    checkSilence();
}

function stopSilenceDetection() {
    if (silenceTimer) cancelAnimationFrame(silenceTimer);
    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
}

async function processAudio(audioBlob) {
    const reader = new FileReader();
    reader.onloadend = async () => {
        const base64Audio = reader.result;
        statusText.textContent = "⏳ Transcribing and thinking...";
        console.log("🧠 Sending audio to backend...");

        try {
            const response = await fetch("/submitAudio", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ audio: base64Audio })
            });

            const result = await response.json();

            if (result.error) {
                transcriptionText.textContent = "❌ Error: " + result.error;
                statusText.textContent = "❌ Error occurred";
                return;
            }

            transcriptionText.textContent = result.transcript;
            responseText.textContent = result.response;

            statusText.textContent = "🔊 Speaking...";
            console.log("✅ Response:", result.response);

            const streamUrl = `/stream-audio?text=${encodeURIComponent(result.response)}`;
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

            audioPlayer.play().then(() => {
                console.log("▶️ Audio playing...");
            }).catch(err => {
                console.warn("⚠️ Playback error:", err);
            });

            let done = false;
            preMicStarted = false;

            audioPlayer.ontimeupdate = () => {
                if (!preMicStarted && audioPlayer.duration > 0 &&
                    audioPlayer.currentTime > audioPlayer.duration - 1.0) {
                    preMicStarted = true;
                    prepareMic();
                }

                if (audioPlayer.duration > 0 &&
                    audioPlayer.currentTime > 0 &&
                    Math.abs(audioPlayer.duration - audioPlayer.currentTime) < 0.3 &&
                    !done) {
                    done = true;
                    console.log("🔁 Repeating loop via time check...");
                    statusText.textContent = "🎤 Listening...";
                    startAssistant();
                }
            };

            setTimeout(() => {
                if (!done) {
                    console.log("⏱️ Timeout fallback triggered.");
                    statusText.textContent = "🎤 Listening...";
                    startAssistant();
                }
            }, 10000);

        } catch (err) {
            console.error("❌ Audio send error:", err);
            transcriptionText.textContent = "❌ Error sending audio.";
            statusText.textContent = "❌ Failed to contact server.";
        }
    };
    reader.readAsDataURL(audioBlob);
}
