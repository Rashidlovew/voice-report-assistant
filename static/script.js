let isRecording = false;
let mediaRecorder;
let audioChunks = [];
let audioContext;
let analyser;
let sourceNode;
let silenceTimer;

const startBtn = document.getElementById("startBtn");
const transcriptionText = document.getElementById("transcriptionText");
const responseText = document.getElementById("responseText");
const audioPlayer = document.getElementById("audioPlayer");

startBtn.addEventListener("click", async () => {
    startBtn.disabled = true;
    startAssistant();
});

async function startAssistant() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    audioContext = new AudioContext();
    sourceNode = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    sourceNode.connect(analyser);

    mediaRecorder = new MediaRecorder(stream);
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
    detectSilence(() => {
        if (isRecording) {
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
        const isSilent = buffer.every(val => val < threshold * 256);

        if (isSilent) {
            if (performance.now() - silenceStart > timeout) {
                onSilence();
                return;
            }
        } else {
            silenceStart = performance.now(); // Reset timer
        }

        silenceTimer = requestAnimationFrame(checkSilence);
    }

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

            // 🔊 Play response using ElevenLabs streaming
            const streamUrl = `/stream-audio?text=${encodeURIComponent(result.response)}`;
            const mediaSource = new MediaSource();
            audioPlayer.src = URL.createObjectURL(mediaSource);

            mediaSource.addEventListener("sourceopen", () => {
                const sourceBuffer = mediaSource.addSourceBuffer("audio/mpeg");
                fetch(streamUrl).then(res => {
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
                startAssistant(); // 🔁 Loop again
            };
        } catch (err) {
            console.error("❌ Audio send error:", err);
            transcriptionText.textContent = "❌ Error sending audio.";
        }
    };
    reader.readAsDataURL(audioBlob);
}
