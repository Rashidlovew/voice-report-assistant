let isRecording = false;
let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start-button");
const statusText = document.getElementById("status");
const responseArea = document.getElementById("response");

startButton.addEventListener("click", async () => {
    if (!isRecording) {
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
                    const response = await fetch("/submitAudio", {
                        method: "POST",
                        headers: {
                            "Content-Type": "application/json"
                        },
                        body: JSON.stringify({ audio: base64Audio })
                    });

                    const result = await response.json();

                    if (result.error) {
                        statusText.innerText = "❌ Error: " + result.error;
                        return;
                    }

                    // Display the result
                    responseArea.value += `\n👤 أنت: ${result.transcript}\n🤖 AI: ${result.response}\n`;
                    statusText.innerText = "🤖 AI: " + result.response;

                    // FIX: Ensure audio plays properly by converting base64 to Blob URL
                    const audioBlob = await (await fetch("data:audio/mp3;base64," + result.audio)).blob();
                    const audioUrl = URL.createObjectURL(audioBlob);
                    const audio = new Audio(audioUrl);
                    audio.play();

                    // Automatically start next recording after AI speaks
                    audio.onended = () => startButton.click();

                } catch (err) {
                    console.error(err);
                    statusText.innerText = "❌ Error sending audio.";
                }
            };
            reader.readAsDataURL(audioBlob);
        });

        mediaRecorder.start();
        statusText.innerText = "🎤 Recording... please speak.";
        startButton.innerText = "⏹️ Stop";
        isRecording = true;
    } else {
        mediaRecorder.stop();
        startButton.innerText = "🎙️ Start Talking";
        isRecording = false;
    }
});
