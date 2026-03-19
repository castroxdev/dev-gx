const messagesEl = document.getElementById("messages");
const statusTextEl = document.getElementById("statusText");
const ollamaStatusEl = document.getElementById("ollamaStatus");
const ollamaDetailEl = document.getElementById("ollamaDetail");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("messageInput");
const sendButtonEl = document.getElementById("sendButton");
const clearButtonEl = document.getElementById("clearButton");
const promptButtons = document.querySelectorAll("[data-prompt]");

let messages = [];
let isLoading = false;


function renderMessage(role, content) {
  const bubble = document.createElement("article");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}


function setLoading(loading) {
  isLoading = loading;
  inputEl.disabled = loading;
  sendButtonEl.disabled = loading;
  clearButtonEl.disabled = loading;
  statusTextEl.textContent = loading ? "A gerar resposta..." : "Pronto.";
}


function setOllamaStatus(status, detail) {
  const visualStatus = status === "online" ? "online" : status === "degraded" ? "degraded" : "offline";

  ollamaStatusEl.classList.remove("online", "offline", "degraded");
  ollamaStatusEl.classList.add(visualStatus);

  if (status === "online") {
    ollamaStatusEl.textContent = "Online";
  } else if (status === "degraded") {
    ollamaStatusEl.textContent = "Modelo ausente";
  } else {
    ollamaStatusEl.textContent = "Offline";
  }

  ollamaDetailEl.textContent = detail;
}


async function loadOllamaStatus() {
  try {
    const response = await fetch("/api/health/ollama");
    const data = await response.json();

    if (!response.ok) {
      throw new Error("Falha ao consultar o estado do Ollama.");
    }

    setOllamaStatus(
      data.status,
      `${data.detail} Modelo configurado: ${data.model}. Endpoint: ${data.base_url}.`
    );
  } catch (error) {
    setOllamaStatus("offline", `Nao foi possivel verificar o Ollama: ${error.message}`);
  }
}


function resetChat() {
  if (isLoading) {
    return;
  }

  messages = [];
  messagesEl.innerHTML = "";
  renderMessage(
    "assistant",
    "Ola! Posso planear o teu produto, modelar entidades e gerar um esquema SQL inicial. Diz-me o que queres construir."
  );
  inputEl.focus();
}


async function sendMessage() {
  if (isLoading) {
    return;
  }

  const content = inputEl.value.trim();
  if (!content) {
    return;
  }

  messages.push({ role: "user", content });
  renderMessage("user", content);
  inputEl.value = "";
  setLoading(true);

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages })
    });

    const rawText = await response.text();

    if (!response.ok) {
      throw new Error(`POST /api/chat falhou com HTTP ${response.status}: ${rawText}`);
    }

    const data = JSON.parse(rawText);
    messages.push({ role: "assistant", content: data.reply });
    renderMessage("assistant", data.reply);
  } catch (error) {
    renderMessage("assistant", `Erro: ${error.message}`);
  } finally {
    setLoading(false);
    inputEl.focus();
    await loadOllamaStatus();
  }
}


formEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  await sendMessage();
});


inputEl.addEventListener("keydown", async (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    await sendMessage();
  }
});


clearButtonEl.addEventListener("click", resetChat);


promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    inputEl.value = button.dataset.prompt;
    inputEl.focus();
  });
});


resetChat();
loadOllamaStatus();
