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

function createMessageElement(role, content = "") {
  const bubble = document.createElement("article");
  bubble.className = `message ${role}`;
  bubble.textContent = content;
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

function renderMessage(role, content) {
  createMessageElement(role, content);
}

function updateMessage(element, content) {
  element.textContent = content;
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(loading) {
  isLoading = loading;
  inputEl.disabled = loading;
  sendButtonEl.disabled = loading;
  clearButtonEl.disabled = loading;
  statusTextEl.textContent = loading ? "A gerar resposta em tempo real..." : "Pronto.";
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

  const userMessage = { role: "user", content };
  messages.push(userMessage);
  renderMessage("user", content);
  inputEl.value = "";
  setLoading(true);

  const assistantBubble = createMessageElement("assistant", "");
  let assistantText = "";

  try {
    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages })
    });

    if (!response.ok || !response.body) {
      const rawText = await response.text();
      throw new Error(`POST /api/chat/stream falhou com HTTP ${response.status}: ${rawText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      while (buffer.includes("\n\n")) {
        const boundary = buffer.indexOf("\n\n");
        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);

        if (!rawEvent.trim()) {
          continue;
        }

        const lines = rawEvent.split("\n");
        let eventName = "message";
        const dataLines = [];

        for (const line of lines) {
          if (line.startsWith("event:")) {
            eventName = line.slice(6).trim();
          } else if (line.startsWith("data:")) {
            let chunk = line.slice(5);
            if (chunk.startsWith(" ")) {
              chunk = chunk.slice(1);
            }
            dataLines.push(chunk);
          }
        }

        const data = dataLines.join("\n")
          .replace(/\\\\/g, "\\")
          .replace(/\\n/g, "\n");

        if (eventName === "error") {
          throw new Error(data);
        }

        if (eventName === "done") {
          continue;
        }

        assistantText += data;
        updateMessage(assistantBubble, assistantText);
      }
    }

    assistantText += decoder.decode();
    assistantText = assistantText.trim();

    if (!assistantText) {
      throw new Error("O streaming terminou sem devolver conteudo.");
    }

    messages.push({ role: "assistant", content: assistantText });
  } catch (error) {
    const errorMessage = `Erro: ${error.message}`;
    updateMessage(assistantBubble, errorMessage);
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
