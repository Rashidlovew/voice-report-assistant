let mediaRecorder;
let audioChunks = [];

const startButton = document.getElementById("start");
const stopButton = document.getElementById("stop");
const player = document.getElementById("player");

startButton.onclick = async () => {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mediaRecorder = new MediaRecorder(stream);
  audioChunks = [];

  mediaRecorder.ondataavailable = (e) => {
    audioChunks.push(e.data);
  };

  mediaRecorder.onstop = async () => {
    const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
    const formData = new FormData();
    formData.append("audio", audioBlob, "voice.webm");

    const response = await fetch("/voice", {
      method: "POST",
      body: formData,
    });

    if (response.ok) {
      const blob = await response.blob();
      const audioURL = URL.createObjectURL(blob);
      player.src = audioURL;
      player.play();
    } else {
      alert("حدث خطأ أثناء إرسال الصوت.");
    }
  };

  mediaRecorder.start();
  startButton.disabled = true;
  stopButton.disabled = false;
};

stopButton.onclick = () => {
  mediaRecorder.stop();
  startButton.disabled = false;
  stopButton.disabled = true;
};
