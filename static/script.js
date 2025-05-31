let mediaRecorder;
let audioChunks = [];

function startConversation() {
    fetch("/start", { method: "POST" })
        .then(res => res.json())
        .then(data => {
            document.getElementById("prompt").innerText = `🎧 استمع إلى: ${data.prompt}`;
            document.getElementById("transcript").placeholder = data.prompt;
            playAudio(data.audio);
        });
}

function playAudio(audioBytes) {
    const blob = new Blob([new Uint8Array(audioBytes)], { type: "audio/mpeg" });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);
    audio.play().catch(err => {
        console.error("Audio playback error:", err);
        document.getElementById("prompt").innerHTML = "❌ لم يتم تشغيل الصوت.";
    });
}

function startRecording() {
    navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
        mediaRecorder = new MediaRecorder(stream);
        mediaRecorder.start();
        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
            audioChunks.push(event.data);
        });

        mediaRecorder.addEventListener("stop", () => {
            const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
            const formData = new FormData();
            formData.append("audio", audioBlob);

            fetch("/listen", {
                method: "POST",
                body: formData
            })
                .then(res => res.json())
                .then(data => {
                    document.getElementById("prompt").innerText = `🎧 استمع إلى: ${data.prompt}`;
                    document.getElementById("transcript").value = data.text;
                    playAudio(data.audio);
                });
        });

        setTimeout(() => {
            mediaRecorder.stop();
        }, 7000);
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("startButton").addEventListener("click", startConversation);
    document.getElementById("transcript").addEventListener("focus", startRecording);
});
