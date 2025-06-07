let mediaRecorder;
let audioChunks = [];
let currentField = "";
let silenceTimeout;
let recording = false;

const startRecording = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    mediaRecorder = new MediaRecorder(stream);
    audioChunks = [];

    mediaRecorder.ondataavailable = (event) => {
        audioChunks.push(event.data);
    };

    mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        const base64Audio = await blobToBase64(audioBlob);

        const formData = new FormData();
        formData.append("file", audioBlob, "audio.webm");

        const res = await fetch("/transcribe", {
            method: "POST",
            body: formData
        });

        const { text } = await res.json();
        appendMessage("أنت", text);

        const replyRes = await fetch("/speak", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text })
        });

        const replyData = await replyRes.json();
        const reply = replyData.reply;
        const audioResponse = await fetch("/audio", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: reply })
        });

        const audioBlob = await audioResponse.blob();
        const audioUrl = URL.createObjectURL(audioBlob);
        const audio = new Audio(audioUrl);
        audio.play();

        appendMessage("المساعد", reply);

        if (replyData.done) {
            document.getElementById("start-btn").disabled = true;
        }
    };

    mediaRecorder.start();
    recording = true;
    startSilenceDetection();
};

const stopRecording = () => {
    if (mediaRecorder && recording) {
        mediaRecorder.stop();
        recording = false;
    }
    clearTimeout(silenceTimeout);
};

const startSilenceDetection = () => {
    clearTimeout(silenceTimeout);
    silenceTimeout = setTimeout(() => {
        stopRecording();
    }, 4000); // 4 seconds silence timeout
};

const blobToBase64 = (blob) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => resolve(reader.result.split(",")[1]);
        reader.onerror = reject;
        reader.readAsDataURL(blob);
    });
};

const appendMessage = (sender, text) => {
    const chat = document.getElementById("chat");
    const div = document.createElement("div");
    div.className = sender === "أنت" ? "user" : "assistant";
    div.innerText = text;
    chat.appendChild(div);
    chat.scrollTop = chat.scrollHeight;
};

document.getElementById("start-btn").onclick = async () => {
    appendMessage("المساعد", "🎙️ تفضل بالتحدث...");
    await startRecording();
};