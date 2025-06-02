let recorder;
let audioChunks = [];

async function startRecording() {
    audioChunks = [];
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    recorder = new MediaRecorder(stream);
    recorder.ondataavailable = e => audioChunks.push(e.data);
    recorder.onstop = sendAudio;
    recorder.start();
    document.getElementById("status").textContent = "🎙️ Recording...";
}

function stopRecording() {
    recorder.stop();
    document.getElementById("status").textContent = "🔄 Processing...";
}

async function sendAudio() {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const reader = new FileReader();
    reader.onloadend = async () => {
        const base64Audio = reader.result;

        const response = await fetch("/submitAudio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio: base64Audio })
        });

        const data = await response.json();

        if (data.error) {
            alert("❌ Error: " + data.error);
            return;
        }

        // Display results
        document.getElementById("originalText").textContent = "📝 Transcript: " + data.transcript;
        document.getElementById("responseText").textContent = "🤖 GPT: " + data.response;

        // 🔊 Play streaming voice
        const audio = new Audio(data.audio_url);
        audio.play();
    };

    reader.readAsDataURL(audioBlob);
}
