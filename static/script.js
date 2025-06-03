let mediaRecorder;
let audioChunks = [];

const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const transcriptText = document.getElementById("transcriptText");
const responseText = document.getElementById("responseText");

startBtn.onclick = async () => {
  startBtn.disabled = true;
  stopBtn.disabled = false;

  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = event => {
    if (event.data.size > 0) audioChunks.push(event.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const reader = new FileReader();

    reader.onloadend = async () => {
      const base64Audio = reader.result;

      const response = await fetch("/submitAudio", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ audio: base64Audio })
      });

      const result = await response.json();

      if (result.transcript) transcriptText.textContent = result.transcript;
      if (result.response) responseText.textContent = result.response;

      if (result.audio) {
        const audio = new Audio(`data:audio/mpeg;base64,${result.audio}`);
        audio.play();
      }
    };

    reader.readAsDataURL(audioBlob);
  };

  mediaRecorder.start();
};

stopBtn.onclick = () => {
  stopBtn.disabled = true;
  startBtn.disabled = false;
  mediaRecorder.stop();
};
