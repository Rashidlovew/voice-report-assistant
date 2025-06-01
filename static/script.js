document.addEventListener("DOMContentLoaded", () => {
    let isRecording = false;
    let mediaRecorder;
    let audioChunks = [];

    const startButton = document.getElementById("start-button");
    const statusText = document.getElementById("status");
    const responseArea = document.getElementById("response");

    startButton.addEventListener("click", async () => {
        if (!isRecording) {
            try {
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
                            statusText.innerText = "⏳ Processing...";
                            const response = await fetch("/submitAudio", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ audio: base64Audio })
                            });

                            const result = await response.json();
                            responseArea.value = result.transcript + "\n\n" + result.response;
                            statusText.innerText = "🤖 AI: " + result.response;

                            const audio = new Audio("data:audio/mp3;base64," + result.audio);
                            audio.play();

                            // Wait until audio ends before restarting
                            audio.onended = () => {
                                startButton.click();
                            };
                        } catch (err) {
                            console.error(err);
                            statusText.innerText = "❌ Error processing audio.";
                        }
                    };
                    reader.readAsDataURL(audioBlob);
                });

                mediaRecorder.start();
                statusText.innerText = "🎤 Listening... please speak.";
                startButton.innerText = "⏹️ Stop";
                isRecording = true;
            } catch (error) {
                console.error("Microphone access error:", error);
                statusText.innerText = "❌ Cannot access microphone.";
            }
        } else {
            mediaRecorder.stop();
            startButton.innerText = "🎙️ Start Talking";
            isRecording = false;
        }
    });
});
