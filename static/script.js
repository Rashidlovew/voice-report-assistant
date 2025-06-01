let isRecording = false;
let mediaRecorder;
let audioChunks = [];

async function startRecording() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = event => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const blob = new Blob(audioChunks, { type: 'audio/webm' });
        const base64Audio = await blobToBase64(blob);

        const response = await fetch("/submitAudio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ audio: base64Audio })
        });

        const result = await response.json();
        document.getElementById("response").innerText = result.text;

        if (!result.done) {
            const audio = new Audio("data:audio/mp3;base64," + result.audio);
            audio.onended = () => startRecording(); // loop
            audio.play();
        }
    };

    mediaRecorder.start();
    setTimeout(() => mediaRecorder.stop(), 5000); // 5 seconds limit
}

async function blobToBase64(blob) {
    return new Promise((resolve, _) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result);
        reader.readAsDataURL(blob);
    });
}

async function init() {
    const response = await fetch("/start", { method: "POST" });
    const data = await response.json();

    const voiceResponse = await fetch("/fieldPrompt");
    const { prompt } = await voiceResponse.json();

    const reply = await fetch("/submitAudio", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ audio: "" })
    });

    const audio = new Audio("data:audio/mp3;base64," + (await reply.json()).audio);
    audio.onended = () => startRecording();
    audio.play();
}

window.onload = init;
