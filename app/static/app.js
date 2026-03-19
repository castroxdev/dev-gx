const messagesEl = document.getElementById("messages");
const statusTextEl = document.getElementById("statusText");
const ollamaStatusEl = document.getElementById("ollamaStatus");
const ollamaDetailEl = document.getElementById("ollamaDetail");
const formEl = document.getElementById("chatForm");
const inputEl = document.getElementById("messageInput");
const sendButtonEl = document.getElementById("sendButton");
const stopButtonEl = document.getElementById("stopButton");
const clearButtonEl = document.getElementById("clearButton");
const newConversationSidebarButtonEl = document.getElementById("newConversationSidebarButton");
const conversationListEl = document.getElementById("conversationList");
const promptButtons = document.querySelectorAll("[data-prompt]");

const SQL_TERMS = [
  "sql",
  "schema",
  "base de dados",
  "banco de dados",
  "base de datos",
  "database",
  "tabela",
  "tabelas",
  "tabla",
  "tablas",
  "postgres",
  "postgresql",
  "sqlite",
  "mysql",
  "relacao",
  "relacoes",
  "relacion",
  "relaciones"
];

const CONVERSATION_STORAGE_KEY = "devgx.currentConversationId";

let messages = [];
let isLoading = false;
let currentAbortController = null;
let stopRequested = false;
let currentConversationId = null;
let conversationBootstrapPromise = null;
let conversationSummaries = [];

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function normalizeText(text) {
  return text
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

function isSqlIntent(text) {
  const normalized = normalizeText(text || "");
  return SQL_TERMS.some((term) => normalized.includes(term));
}

function extractSqlBlock(text) {
  const fenced = text.match(/```sql\s*([\s\S]*?)```/i);
  if (fenced) {
    return fenced[1].trim();
  }

  if (/create\s+table|alter\s+table|create\s+index|insert\s+into/i.test(text)) {
    return text.trim();
  }

  return null;
}

function formatAssistantContent(text) {
  const sql = extractSqlBlock(text);
  if (!sql) {
    return `<div class="message-text">${escapeHtml(text).replace(/\n/g, "<br>")}</div>`;
  }

  let intro = text;
  const fenced = text.match(/```sql\s*[\s\S]*?```/i);
  if (fenced) {
    intro = text.replace(fenced[0], "").trim();
  } else {
    intro = "";
  }

  const introHtml = intro
    ? `<div class="message-text">${escapeHtml(intro).replace(/\n/g, "<br>")}</div>`
    : "";

  return `${introHtml}<div class="sql-block"><div class="sql-label">SQL</div><pre><code>${escapeHtml(sql)}</code></pre></div>`;
}

function createMessageElement(role, content = "") {
  const bubble = document.createElement("article");
  bubble.className = `message ${role}`;

  const contentEl = document.createElement("div");
  contentEl.className = "message-content";
  if (role === "assistant") {
    contentEl.innerHTML = formatAssistantContent(content);
  } else {
    contentEl.textContent = content;
  }

  bubble.appendChild(contentEl);
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

function renderMessage(role, content) {
  return createMessageElement(role, content);
}

function updateMessage(element, content) {
  const contentEl = element.querySelector(".message-content");
  if (!contentEl) {
    return;
  }

  if (element.classList.contains("assistant")) {
    contentEl.innerHTML = formatAssistantContent(content);
  } else {
    contentEl.textContent = content;
  }

  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function setLoading(loading) {
  isLoading = loading;
  inputEl.disabled = loading;
  sendButtonEl.disabled = loading;
  stopButtonEl.disabled = !loading;
  clearButtonEl.disabled = loading;
  newConversationSidebarButtonEl.disabled = loading;
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

function renderConversationMessages() {
  messagesEl.innerHTML = "";

  if (!messages.length) {
    renderMessage(
      "assistant",
      "Ola! Posso planear o teu produto, modelar entidades e gerar um esquema SQL inicial. Diz-me o que queres construir."
    );
    return;
  }

  messages.forEach((message, index) => {
    const bubble = renderMessage(message.role, message.content);
    if (message.role === "assistant" && index > 0) {
      const previousMessage = messages[index - 1];
      if (previousMessage?.role === "user" && isSqlIntent(previousMessage.content)) {
        attachSqlButton(bubble, previousMessage.content);
      }
    }
  });
}

function renderConversationList() {
  conversationListEl.innerHTML = "";

  if (!conversationSummaries.length) {
    const emptyState = document.createElement("div");
    emptyState.className = "conversation-empty";
    emptyState.textContent = "Ainda nao tens conversas guardadas.";
    conversationListEl.appendChild(emptyState);
    return;
  }

  conversationSummaries.forEach((conversation) => {
    const item = document.createElement("div");
    item.className = "conversation-item";
    if (conversation.id === currentConversationId) {
      item.classList.add("active");
    }

    const openButton = document.createElement("button");
    openButton.type = "button";
    openButton.className = "conversation-open-button";

    const title = document.createElement("div");
    title.className = "conversation-item-title";
    title.textContent = conversation.title || "Nova conversa";

    openButton.appendChild(title);
    openButton.addEventListener("click", async () => {
      if (isLoading || conversation.id === currentConversationId) {
        return;
      }

      statusTextEl.textContent = "A abrir conversa...";

      try {
        await loadConversation(conversation.id);
        statusTextEl.textContent = "Conversa carregada.";
        inputEl.focus();
      } catch (error) {
        statusTextEl.textContent = `Falha ao abrir conversa: ${error.message}`;
      }
    });

    const deleteButton = document.createElement("button");
    deleteButton.type = "button";
    deleteButton.className = "conversation-delete-button";
    deleteButton.textContent = "Apagar";
    deleteButton.addEventListener("click", async (event) => {
      event.stopPropagation();
      if (isLoading) {
        return;
      }

      const confirmed = window.confirm(`Apagar a conversa \"${conversation.title || "Nova conversa"}\"?`);
      if (!confirmed) {
        return;
      }

      statusTextEl.textContent = "A apagar conversa...";

      try {
        await deleteConversation(conversation.id);
        statusTextEl.textContent = "Conversa apagada.";
      } catch (error) {
        statusTextEl.textContent = `Falha ao apagar conversa: ${error.message}`;
      }
    });

    item.appendChild(openButton);
    item.appendChild(deleteButton);
    conversationListEl.appendChild(item);
  });
}

function setCurrentConversationId(conversationId) {
  currentConversationId = conversationId;
  if (conversationId) {
    localStorage.setItem(CONVERSATION_STORAGE_KEY, conversationId);
  } else {
    localStorage.removeItem(CONVERSATION_STORAGE_KEY);
  }
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const rawText = await response.text();
  let data = null;

  if (rawText) {
    try {
      data = JSON.parse(rawText);
    } catch (error) {
      throw new Error(`Resposta invalida de ${url}: ${rawText}`);
    }
  }

  if (!response.ok) {
    const detail = data?.detail || rawText || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

async function createConversationOnServer() {
  return fetchJson("/api/conversations", {
    method: "POST"
  });
}

async function listConversationsFromServer() {
  return fetchJson("/api/conversations");
}

async function loadConversationFromServer(conversationId) {
  return fetchJson(`/api/conversations/${conversationId}`);
}

async function deleteConversationOnServer(conversationId) {
  await fetchJson(`/api/conversations/${conversationId}`, {
    method: "DELETE"
  });
}

async function refreshConversationList() {
  conversationSummaries = await listConversationsFromServer();
  renderConversationList();
}

async function syncConversationOnServer() {
  if (!currentConversationId) {
    return;
  }

  await fetchJson(`/api/conversations/${currentConversationId}`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ messages })
  });

  await refreshConversationList();
}

async function loadConversation(conversationId) {
  const conversation = await loadConversationFromServer(conversationId);
  setCurrentConversationId(conversation.id);
  messages = conversation.messages.map((message) => ({
    role: message.role,
    content: message.content
  }));
  renderConversationMessages();
  renderConversationList();
}

async function createFreshConversation() {
  const conversation = await createConversationOnServer();
  setCurrentConversationId(conversation.id);
  messages = [];
  await refreshConversationList();
  renderConversationMessages();
}

async function deleteConversation(conversationId) {
  const deletingCurrentConversation = conversationId === currentConversationId;

  await deleteConversationOnServer(conversationId);
  await refreshConversationList();

  if (!deletingCurrentConversation) {
    return;
  }

  if (conversationSummaries.length > 0) {
    await loadConversation(conversationSummaries[0].id);
    return;
  }

  setCurrentConversationId(null);
  await createFreshConversation();
}

async function ensureConversationReady() {
  if (conversationBootstrapPromise) {
    return conversationBootstrapPromise;
  }

  conversationBootstrapPromise = (async () => {
    const savedConversationId = localStorage.getItem(CONVERSATION_STORAGE_KEY);
    await refreshConversationList();

    if (savedConversationId && conversationSummaries.some((item) => item.id === savedConversationId)) {
      await loadConversation(savedConversationId);
      return;
    }

    if (conversationSummaries.length > 0) {
      await loadConversation(conversationSummaries[0].id);
      return;
    }

    await createFreshConversation();
  })();

  try {
    await conversationBootstrapPromise;
  } finally {
    conversationBootstrapPromise = null;
  }
}

async function startNewConversation() {
  if (isLoading) {
    return;
  }

  statusTextEl.textContent = "A criar nova conversa...";

  try {
    await createFreshConversation();
    statusTextEl.textContent = "Nova conversa pronta.";
    inputEl.focus();
  } catch (error) {
    statusTextEl.textContent = `Falha ao criar conversa: ${error.message}`;
  }
}

function triggerSqlDownload(fileName, sql) {
  const blob = new Blob([sql], { type: "application/sql;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

async function requestSqlFile(idea) {
  return fetchJson("/api/sql-schema", {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ idea })
  });
}

function attachSqlButton(messageElement, idea) {
  if (!messageElement || !idea || messageElement.querySelector(".message-sql-button")) {
    return;
  }

  messageElement.classList.add("with-action");

  const button = document.createElement("button");
  button.type = "button";
  button.className = "message-sql-button";
  button.textContent = "Baixar .sql";

  button.addEventListener("click", async () => {
    if (isLoading) {
      return;
    }

    const originalLabel = button.textContent;
    button.disabled = true;
    button.textContent = "A gerar...";
    statusTextEl.textContent = "A gerar ficheiro SQL...";

    try {
      const data = await requestSqlFile(idea);
      triggerSqlDownload(data.file_name, data.sql);
      statusTextEl.textContent = `SQL gerado: ${data.file_name}`;
    } catch (error) {
      renderMessage("assistant", `Erro ao gerar SQL: ${error.message}`);
      statusTextEl.textContent = "Falha ao gerar SQL.";
    } finally {
      button.disabled = false;
      button.textContent = originalLabel;
      await loadOllamaStatus();
    }
  });

  messageElement.appendChild(button);
}

function stopStreaming() {
  if (!isLoading || !currentAbortController) {
    return;
  }

  stopRequested = true;
  statusTextEl.textContent = "A interromper resposta...";
  currentAbortController.abort();
}

async function sendMessage() {
  if (isLoading) {
    return;
  }

  await ensureConversationReady();

  const content = inputEl.value.trim();
  if (!content) {
    return;
  }

  const userMessage = { role: "user", content };
  const shouldOfferSql = isSqlIntent(content);

  messages.push(userMessage);
  renderMessage("user", content);
  inputEl.value = "";
  stopRequested = false;
  setLoading(true);

  const assistantBubble = createMessageElement("assistant", "");
  let assistantText = "";

  try {
    currentAbortController = new AbortController();

    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({ messages }),
      signal: currentAbortController.signal
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
    await syncConversationOnServer();

    if (shouldOfferSql) {
      attachSqlButton(assistantBubble, content);
    }
  } catch (error) {
    if (error.name === "AbortError" || stopRequested) {
      assistantText = assistantText.trim();

      if (assistantText) {
        updateMessage(assistantBubble, `${assistantText}\n\n[Resposta interrompida]`);
        messages.push({ role: "assistant", content: `${assistantText}\n\n[Resposta interrompida]` });
      } else {
        updateMessage(assistantBubble, "[Resposta interrompida]");
      }

      await syncConversationOnServer();
      statusTextEl.textContent = "Resposta interrompida.";
    } else {
      updateMessage(assistantBubble, `Erro: ${error.message}`);
      await syncConversationOnServer();
      statusTextEl.textContent = "Falha ao comunicar com o Ollama.";
    }
  } finally {
    currentAbortController = null;
    stopRequested = false;
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

stopButtonEl.addEventListener("click", stopStreaming);
clearButtonEl.addEventListener("click", startNewConversation);
newConversationSidebarButtonEl.addEventListener("click", startNewConversation);

promptButtons.forEach((button) => {
  button.addEventListener("click", () => {
    inputEl.value = button.dataset.prompt;
    inputEl.focus();
  });
});

renderConversationMessages();
renderConversationList();
ensureConversationReady().catch((error) => {
  statusTextEl.textContent = `Falha ao carregar memoria: ${error.message}`;
});
loadOllamaStatus();

