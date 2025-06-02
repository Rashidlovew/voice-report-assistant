let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

// ✅ Correct base64 decoding to binary buffer → blob → voice
function playAudioFromBase64(base64Audio) {
    const binary = Uint8Array.from(atob(base64Audio), c => c.charCodeAt(0));
    const blob = new Blob([binary], { type: 'audio/mpeg' });
    const url = URL.createObjectURL(blob);
    const audio = new Audio(url);

    audio.play().catch(err => console.error("🔴 Audio play error:", err));
    audio.onended = () => setTimeout(() => startButton.click(), 300); // auto-loop
}

startButton.addEventListener("click", async () => {
    if (!isRecording) {
        // 🎤 Start listening
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder = new MediaRecorder(stream);
        audioChunks = [];

        mediaRecorder.addEventListener("dataavailable", event => {
