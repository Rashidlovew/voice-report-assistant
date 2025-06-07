document.addEventListener("DOMContentLoaded", () => {
  const startButton = document.getElementById("startButton");
  startButton.addEventListener("click", startConversation);
});

async function startConversation() {
  appendMessage("assistant", "🔊 جاري بدء المحادثة...");
  await speakAndListen("/next");
}

async function speakAndListen(endpoint) {
  try {
    const response = await fetch(endpoint);
    const data = await response.json();
    appendMessage("assistant", data.text);

    const tts = new Audio();
    tts.src = `/speak?text=${encodeURIComponent(data.text)}`;
    tts.play();

    // Start recording after short delay
    tts.onended = () => {
      startRecording();
    };
  } catch (error) {
    console.error("حدث خطأ:", error);
  }
}

function appendMessage(sender, text) {
  const chat = document.getElementById("chat");
  const msg = document.createElement("div");
  msg.className = sender;
  msg.innerHTML = `<strong>${sender === "user" ? "👤 أنت" : "🤖 المساعد"}:</strong> ${text}`;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}

function startRecording() {
  // Placeholder for actual mic code (already implemented in your project)
  console.log("🎙️ بدء التسجيل...");
}
