let mediaRecorder;
let audioChunks = [];
let currentFieldIndex = 0;

const fields = ["Date", "Briefing", "LocationObservations", "Examination", "Outcomes", "TechincalOpinion"];

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
    const blob = new Blob([new Uint8Array(audioBytes)], { type: "audio/mpeg" }); // ✅ Fix: explicitly declare MP3
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
        }, 7000); // Adjust as needed
    });
}

document.addEventListener("DOMContentLoaded", () => {
    document.getElementById("startButton").addEventListener("click", startConversation);

    const transcriptBox = document.getElementById("transcript");
    transcriptBox.addEventListener("focus", startRecording);
});
