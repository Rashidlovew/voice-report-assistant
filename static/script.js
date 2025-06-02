let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

// ✅ Convert base64 → binary → playable audio
function playAudioFromBase64(base64Audio) {
    const byteCharacters = atob(base64Audio);
    const byteNumbers = new Array(byteCharacters.length);
    for (let i = 0; i < byteCharacters.length; i++) {
        byteNumbers[i] = byteCharacters.charCodeAt(i);
    }
    const byteArray = new Uint8Array(byteNumbers);
    const blob = new Blob([byteArray], { type: 'audio/mpeg' }); // or audio/mp3
    const audioUrl = URL.createObjectURL(blob);

    const audio = new Audio(audioUrl);
    audio.play().catch(err => console.error("🔴 Audio play error:", err));

    // ✅ Auto resume conversation when voice finishes
    audio.onended = () => {
        setTimeout(() => startButton.click(), 300); // slight pause for realism
    };
}

startButton.addEventListener("click", async () => {
    if (!isRecording) {
        // 🎤 Start recording
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
                    const response =
