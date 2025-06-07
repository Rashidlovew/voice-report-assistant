document.addEventListener("DOMContentLoaded", () => {
  const startButton = document.getElementById("startButton");
  startButton.addEventListener("click", startConversation);
});

async function startConversation() {
  appendMessage("assistant", "🔊 جاري بدء المحادثة...");
  await speakNext();
}

async function speakNext() {
  const res = await fetch("/next");
  const data = await res.json();
  appendMessage("assistant", data.text);

  const audio = new Audio();
  audio.src = `/speak`;
  await fetch("/speak", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: data.text })
  })
    .then((res) => res.blob())
    .then((blob) => {
      audio.src = URL.createObjectURL(blob);
      audio.play();
    });
}

function appendMessage(sender, text) {
  const chat = document.getElementById("chat");
  const msg = document.createElement("div");
  msg.className = sender;
  msg.innerHTML = `<strong>${sender === "user" ? "👤 أنت" : "🤖 المساعد"}:</strong> ${text}`;
  chat.appendChild(msg);
  chat.scrollTop = chat.scrollHeight;
}
