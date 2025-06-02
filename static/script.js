let mediaRecorder;
let audioChunks = [];
const startBtn = document.getElementById("start");
const stopBtn = document.getElementById("stop");
const responseText = document.getElementById("responseText");

startBtn.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = e => {
    if (e.data.size > 0) audioChunks.push(e.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: "audio/webm" });
    const formData = new FormData();
    formData.append("audio", audioBlob, "recording.webm");

    const res = await fetch("/submitAudio", { method: "POST", body: formData });
    const data = await res.json();
    responseText.textContent = data.text || data.error || "No response.";

    if (data.audio_url) {
      const audio = new Audio(data.audio_url);
      audio.play();
    }
  };

  mediaRecorder.start();
  startBtn.disabled = true;
  stopBtn.disabled = false;
};

stopBtn.onclick = () => {
  mediaRecorder.stop();
  startBtn.disabled = false;
  stopBtn.disabled = true;
};
