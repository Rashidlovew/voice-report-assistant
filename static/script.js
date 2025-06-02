let mediaRecorder;
let audioChunks = [];
let isRecording = false;

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) {
            audioChunks.push(event.data);
        }
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append("file", audioBlob, "recording.wav");

        const response = await fetch("/submitAudio", {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            alert("Error: " + response.status);
            return;
        }

        const data = await response.json();
        const resultText = data.text || "No text returned";
        const audioBase64 = data.audio || null;

        document.getElementById("responseText").innerText = resultText;

        if (audioBase64) {
            const audio = new Audio(audioBase64);
            audio.play();
        } else {
            alert("No audio was returned.");
        }
    };

    mediaRecorder.start();
    isRecording = true;
    document.getElementById("recordButton").innerText = "⏹️ Stop Recording";
}

function stopRecording() {
    mediaRecorder.stop();
    isRecording = false;
    document.getElementById("recordButton").innerText = "🎙️ Start Recording";
}

document.getElementById("recordButton").addEventListener("click", () => {
    if (isRecording) {
        stopRecording();
    } else {
        startRecording();
    }
});
