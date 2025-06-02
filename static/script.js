let mediaRecorder;
let audioChunks = [];

const recordButton = document.getElementById("recordButton");
const stopButton = document.getElementById("stopButton");

recordButton.addEventListener("click", async () => {
  recordButton.disabled = true;
  stopButton.disabled = false;
  audioChunks = [];

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);

  mediaRecorder.ondataavailable = event => {
    if (event.data.size > 0) {
      audioChunks.push(event.data);
    }
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
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
        console.error("❌ Server Error:", data.error);
        document.getElementById("aiResponse").innerText = "❌ Error: " + data.error;
        return;
      }

      document.getElementById("transcript").innerText = "🗣️ قلت: " + data.transcript;
      document.getElementById("aiResponse").innerText = "🤖 المساعد: " + data.response;

      if (data.audio) {
        const audio = new Audio("data:audio/mpeg;base64," + data.audio);
        audio.play();
      } else {
        console.error("⚠️ No audio found in response.");
      }
    };

    reader.readAsDataURL(audioBlob);
  };

  mediaRecorder.start();
});

stopButton.addEventListener("click", () => {
  stopButton.disabled = true;
  recordButton.disabled = false;
  mediaRecorder.stop();
});
