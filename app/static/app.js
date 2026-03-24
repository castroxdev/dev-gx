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
const executionFlowListEl = document.getElementById("executionFlowList");
const executionFlowStatusEl = document.getElementById("executionFlowStatus");
const executionFlowSubtitleEl = document.getElementById("executionFlowSubtitle");
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

const TOOL_PROGRESS_MESSAGES = [
  "A gerar plano MVP...",
  "A criar esquema SQL...",
  "A sugerir endpoints API..."
];

const TOOL_PROGRESS_DETAILS = {
  "A gerar plano MVP...": {
    label: "Plano MVP"
  },
  "A criar esquema SQL...": {
    label: "Esquema SQL"
  },
  "A sugerir endpoints API...": {
    label: "Endpoints API"
  }
};

const CONVERSATION_STORAGE_KEY = "devgx.currentConversationId";

let messages = [];
let isLoading = false;
let isSending = false;
let currentAbortController = null;
let stopRequested = false;
let currentConversationId = null;
let conversationBootstrapPromise = null;
let conversationSummaries = [];
let currentTraceRequestId = null;
let currentTracePollToken = 0;

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

function formatInlineAssistantText(text) {
  return escapeHtml(text).replace(/`([^`]+)`/g, "<code>$1</code>");
}

function renderStructuredAssistantText(text) {
  const lines = (text || "").split("\n");
  const html = [];
  let paragraph = [];
  let listItems = [];
  let endpointItems = [];
  let currentEndpoint = null;

  function flushParagraph() {
    if (!paragraph.length) {
      return;
    }

    const content = paragraph.join("<br>");
    html.push(`<p class="assistant-paragraph">${content}</p>`);
    paragraph = [];
  }

  function flushList() {
    if (!listItems.length) {
      return;
    }

    html.push(`<ul class="assistant-list">${listItems.join("")}</ul>`);
    listItems = [];
  }

  function flushEndpoints() {
    if (currentEndpoint) {
      endpointItems.push(currentEndpoint);
      currentEndpoint = null;
    }

    if (!endpointItems.length) {
      return;
    }

    html.push(`<div class="assistant-endpoints">${endpointItems.join("")}</div>`);
    endpointItems = [];
  }

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      flushParagraph();
      flushList();
      flushEndpoints();
      continue;
    }

    const markdownHeadingMatch = line.match(/^(#{1,3})\s+(.+)$/);
    if (markdownHeadingMatch) {
      flushParagraph();
      flushList();
      flushEndpoints();

      const level = Math.min(markdownHeadingMatch[1].length, 3);
      const content = formatInlineAssistantText(markdownHeadingMatch[2]);
      html.push(`<h${level + 2} class="assistant-heading assistant-heading-${level}">${content}</h${level + 2}>`);
      continue;
    }

    const numberedHeadingMatch = line.match(/^(\d+)\.\s+(.+)$/);
    if (numberedHeadingMatch) {
      flushParagraph();
      flushList();
      flushEndpoints();

      const index = escapeHtml(numberedHeadingMatch[1]);
      const content = formatInlineAssistantText(numberedHeadingMatch[2]);
      html.push(`<h3 class="assistant-heading assistant-heading-numbered"><span class="assistant-heading-index">${index}.</span> ${content}</h3>`);
      continue;
    }

    const endpointMatch = line.match(/^\-\s*(GET|POST|PUT|PATCH|DELETE)\s+([^\s:]+):\s*(.+)$/i);
    if (endpointMatch) {
      flushParagraph();
      flushList();

      if (currentEndpoint) {
        endpointItems.push(currentEndpoint);
      }

      const method = escapeHtml(endpointMatch[1].toUpperCase());
      const path = formatInlineAssistantText(endpointMatch[2]);
      const purpose = formatInlineAssistantText(endpointMatch[3]);

      currentEndpoint = `
        <article class="endpoint-item">
          <div class="endpoint-main">
            <span class="endpoint-method">${method}</span>
            <code class="endpoint-path">${path}</code>
          </div>
          <p class="endpoint-purpose">${purpose}</p>
      `;
      continue;
    }

    if (currentEndpoint && /^request:\s*/i.test(line)) {
      const requestText = formatInlineAssistantText(line.replace(/^request:\s*/i, ""));
      currentEndpoint += `<div class="endpoint-meta"><span class="endpoint-meta-label">Request</span><span class="endpoint-meta-text">${requestText}</span></div>`;
      continue;
    }

    if (currentEndpoint && /^response:\s*/i.test(line)) {
      const responseText = formatInlineAssistantText(line.replace(/^response:\s*/i, ""));
      currentEndpoint += `<div class="endpoint-meta"><span class="endpoint-meta-label">Response</span><span class="endpoint-meta-text">${responseText}</span></div></article>`;
      endpointItems.push(currentEndpoint);
      currentEndpoint = null;
      continue;
    }

    if (/^\-\s+/.test(line)) {
      flushParagraph();
      flushEndpoints();
      listItems.push(`<li>${formatInlineAssistantText(line.replace(/^\-\s+/, ""))}</li>`);
      continue;
    }

    flushList();
    flushEndpoints();
    paragraph.push(formatInlineAssistantText(line));
  }

  flushParagraph();
  flushList();
  flushEndpoints();

  return `<div class="assistant-rich">${html.join("")}</div>`;
}

function formatAssistantContent(text) {
  if (isToolProgressMessage(text)) {
    return escapeHtml(text);
  }

  const sql = extractSqlBlock(text);
  if (!sql) {
    return renderStructuredAssistantText(text);
  }

  let intro = text;
  const fenced = text.match(/```sql\s*[\s\S]*?```/i);
  if (fenced) {
    intro = text.replace(fenced[0], "").trim();
  } else {
    intro = "";
  }

  const introHtml = intro ? renderStructuredAssistantText(intro) : "";

  return `${introHtml}<div class="sql-block"><div class="sql-label">SQL</div><pre><code>${escapeHtml(sql)}</code></pre></div>`;
}

function isToolProgressMessage(text) {
  const normalized = (text || "").trim();
  return TOOL_PROGRESS_MESSAGES.includes(normalized);
}

function getToolProgressDetail(text) {
  const normalized = (text || "").trim();
  return TOOL_PROGRESS_DETAILS[normalized] || null;
}

function buildProgressUiState(progressText) {
  const detail = getToolProgressDetail(progressText);
  return {
    badges: [
      "A executar",
      detail?.label || "Apoio interno"
    ]
  };
}

function buildFallbackUiState(progressText) {
  const detail = getToolProgressDetail(progressText);
  return {
    badges: [
      "Com apoio interno",
      detail?.label || "Apoio interno",
      "Resposta consolidada"
    ]
  };
}

function buildAssistantMeta(uiState) {
  if (!uiState || !Array.isArray(uiState.badges) || !uiState.badges.length) {
    return "";
  }

  const badges = uiState.badges
    .filter((badge) => typeof badge === "string" && badge.trim())
    .map((badge) => `<span class="message-badge">${escapeHtml(badge.trim())}</span>`)
    .join("");

  if (!badges) {
    return "";
  }

  return `<div class="message-meta">${badges}</div>`;
}

function renderMessageContent(role, content, uiState = null) {
  if (role === "assistant") {
    return formatAssistantContent(content);
  }

  return escapeHtml(content);
}
function createMessageElement(role, content = "", variant = "default", uiState = null) {
  const bubble = document.createElement("article");
  bubble.className = `message ${role}`;
  if (variant !== "default") {
    bubble.classList.add(`message-${variant}`);
  }

  const contentEl = document.createElement("div");
  contentEl.className = "message-content";
  contentEl.innerHTML = renderMessageContent(role, content, uiState);

  bubble.appendChild(contentEl);
  messagesEl.appendChild(bubble);
  messagesEl.scrollTop = messagesEl.scrollHeight;
  return bubble;
}

function renderMessage(role, content, variant = "default", uiState = null) {
  return createMessageElement(role, content, variant, uiState);
}

function updateMessage(element, content, uiState = null) {
  const contentEl = element.querySelector(".message-content");
  if (!contentEl) {
    return;
  }

  const role = element.classList.contains("assistant") ? "assistant" : "user";
  contentEl.innerHTML = renderMessageContent(role, content, uiState);

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
    setOllamaStatus("offline", `NÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o foi possÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â­vel verificar o Ollama: ${error.message}`);
  }
}

function renderConversationMessages() {
  messagesEl.innerHTML = "";

  if (!messages.length) {
    renderMessage(
      "assistant",
      "OlÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡! Posso planear o teu produto, modelar entidades e gerar um esquema SQL inicial. Diz-me o que queres construir."
    );
    return;
  }

  messages.forEach((message, index) => {
    const bubble = renderMessage(message.role, message.content, "default", message.uiState || null);
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
    emptyState.textContent = "Ainda nÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â£o tens conversas guardadas.";
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
      throw new Error(`Resposta invÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â¡lida de ${url}: ${rawText}`);
    }
  }

  if (!response.ok) {
    const detail = data?.detail || rawText || `HTTP ${response.status}`;
    throw new Error(detail);
  }

  return data;
}

function getExecutionStatusClass(status) {
  const normalized = String(status || "").trim().toLowerCase();

  if (normalized === "error") {
    return "error";
  }

  if (normalized === "running" || normalized === "started") {
    return "running";
  }

  if (normalized === "success" || normalized === "completed" || normalized === "done") {
    return "done";
  }

  return "idle";
}

function getExecutionStatusLabel(status) {
  const statusClass = getExecutionStatusClass(status);

  if (statusClass === "running") {
    return "Running";
  }

  if (statusClass === "done") {
    return "Done";
  }

  if (statusClass === "error") {
    return "Error";
  }

  return "Idle";
}

function formatDuration(ms) {
  if (typeof ms !== "number" || Number.isNaN(ms) || ms < 0) {
    return "";
  }

  if (ms >= 1000) {
    const seconds = ms / 1000;
    return `${seconds >= 10 ? seconds.toFixed(0) : seconds.toFixed(1)}s`;
  }

  return `${Math.round(ms)}ms`;
}

function setExecutionFlowState(
  status = "idle",
  subtitle = "Passos discretos do pedido atual.",
  body = "Os passos internos do pedido atual aparecem aqui."
) {
  if (!executionFlowListEl || !executionFlowStatusEl || !executionFlowSubtitleEl) {
    return;
  }

  const statusLabel = getExecutionStatusLabel(status);
  const statusClass = getExecutionStatusClass(status);

  executionFlowStatusEl.textContent = statusLabel;
  executionFlowStatusEl.className = `execution-flow-status ${statusClass}`;
  executionFlowSubtitleEl.textContent = subtitle;
  executionFlowListEl.innerHTML = `<div class="execution-flow-empty">${escapeHtml(body)}</div>`;
}

function buildExecutionStepDetail(label, step, trace) {
  const parts = [];

  if (label === "Request received" && typeof step.message_count === "number") {
    parts.push(`${step.message_count} message${step.message_count === 1 ? "" : "s"}`);
  }

  if (
    ["Tool selected", "Tool executed", "Tool result received", "Fallback used"].includes(label)
    && typeof step.tool_name === "string"
    && step.tool_name.trim()
  ) {
    parts.push(step.tool_name.trim());
  }

  if (label === "Tool executed") {
    const duration = formatDuration(step.duration_ms);
    if (duration) {
      parts.push(duration);
    }
  }

  if (label === "Fallback used") {
    if (step.reason === "tool_result_rendered") {
      parts.push("tool output reused");
    } else if (step.reason === "empty_model_response") {
      parts.push("empty model response");
    } else if (step.reason === "invalid_tool_call") {
      parts.push("invalid tool call");
    } else if (step.reason === "tool_error") {
      parts.push("tool error fallback");
    }
  }

  if (label === "Final response sent") {
    const totalDuration = formatDuration(trace?.total_duration_ms);
    if (totalDuration) {
      parts.push(`Total ${totalDuration}`);
    }
  }

  if (step.status === "error" && typeof step.error_detail === "string" && step.error_detail.trim()) {
    parts.push(step.error_detail.trim());
  }

  return parts.join(" · ");
}

function summarizeExecutionTrace(trace) {
  const items = [];
  const steps = Array.isArray(trace?.steps) ? trace.steps : [];

  steps.forEach((step, index) => {
    if (!step || typeof step.stage !== "string") {
      return;
    }

    if (step.stage === "request_received") {
      items.push({
        key: `request-${index}`,
        label: "Request received",
        status: step.status,
        detail: buildExecutionStepDetail("Request received", step, trace)
      });
      return;
    }

    if (step.stage === "tool_call") {
      if (step.status === "started") {
        items.push({
          key: `tool-${index}-selected`,
          label: "Tool selected",
          status: step.status,
          detail: buildExecutionStepDetail("Tool selected", step, trace)
        });
        return;
      }

      items.push({
        key: `tool-${index}-executed`,
        label: "Tool executed",
        status: step.status,
        detail: buildExecutionStepDetail("Tool executed", step, trace)
      });

      if (step.status === "completed" && Object.prototype.hasOwnProperty.call(step, "tool_result")) {
        items.push({
          key: `tool-${index}-result`,
          label: "Tool result received",
          status: "completed",
          detail: buildExecutionStepDetail("Tool result received", step, trace)
        });
      }
      return;
    }

    if (step.stage === "fallback_used") {
      items.push({
        key: `fallback-${index}`,
        label: "Fallback used",
        status: step.status,
        detail: buildExecutionStepDetail("Fallback used", step, trace)
      });
      return;
    }

    if (step.stage === "response_sent") {
      items.push({
        key: `response-${index}`,
        label: "Final response sent",
        status: step.status,
        detail: buildExecutionStepDetail("Final response sent", step, trace)
      });
    }
  });

  return items;
}

function renderExecutionFlow(trace) {
  if (!executionFlowListEl || !executionFlowStatusEl || !executionFlowSubtitleEl) {
    return;
  }

  const items = summarizeExecutionTrace(trace);
  const statusClass = getExecutionStatusClass(trace?.status);
  let subtitle = "Passos discretos do pedido atual.";

  if (statusClass === "running") {
    subtitle = "A acompanhar o pedido atual em tempo real.";
  } else if (statusClass === "error") {
    subtitle = "O pedido atual terminou com erro.";
  } else if (items.length) {
    subtitle = "Último pedido concluído.";
  }

  const totalDuration = formatDuration(trace?.total_duration_ms);
  executionFlowStatusEl.textContent = getExecutionStatusLabel(trace?.status);
  executionFlowStatusEl.className = `execution-flow-status ${statusClass}`;
  executionFlowSubtitleEl.textContent = totalDuration && statusClass !== "running"
    ? `${subtitle} Total ${totalDuration}.`
    : subtitle;

  if (!items.length) {
    executionFlowListEl.innerHTML = '<div class="execution-flow-empty">A aguardar passos do pedido atual.</div>';
    return;
  }

  executionFlowListEl.innerHTML = items.map((item) => {
    const itemStatusClass = getExecutionStatusClass(item.status);
    const detail = item.detail
      ? `<div class="execution-step-detail">${escapeHtml(item.detail)}</div>`
      : "";

    return `
      <article class="execution-step ${itemStatusClass}">
        <div class="execution-step-head">
          <div class="execution-step-title">${escapeHtml(item.label)}</div>
          <div class="execution-step-pill ${itemStatusClass}">${escapeHtml(getExecutionStatusLabel(item.status))}</div>
        </div>
        ${detail}
      </article>
    `;
  }).join("");
}

function resetExecutionFlow() {
  currentTraceRequestId = null;
  currentTracePollToken += 1;
  setExecutionFlowState();
}

async function pollExecutionFlow(requestId, token) {
  if (token !== currentTracePollToken || currentTraceRequestId !== requestId) {
    return;
  }

  try {
    const trace = await fetchJson(`/api/debug/traces/${requestId}`);

    if (token !== currentTracePollToken || currentTraceRequestId !== requestId) {
      return;
    }

    renderExecutionFlow(trace);

    if (getExecutionStatusClass(trace?.status) === "running") {
      window.setTimeout(() => {
        pollExecutionFlow(requestId, token);
      }, 700);
    }
  } catch (error) {
    if (token !== currentTracePollToken || currentTraceRequestId !== requestId) {
      return;
    }

    setExecutionFlowState(
      "error",
      "O fluxo do pedido não pôde ser carregado.",
      "Não foi possível ler o trace deste pedido."
    );
  }
}

function trackExecutionFlow(requestId) {
  if (!requestId) {
    setExecutionFlowState(
      "idle",
      "Passos discretos do pedido atual.",
      "Não foi possível associar o trace a este pedido."
    );
    return;
  }

  currentTraceRequestId = requestId;
  const token = ++currentTracePollToken;

  setExecutionFlowState(
    "running",
    "A acompanhar o pedido atual em tempo real.",
    "A preparar o fluxo do pedido..."
  );

  pollExecutionFlow(requestId, token);
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
    body: JSON.stringify({
      messages: messages.map((message) => ({
        role: message.role,
        content: message.content
      }))
    })
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
  resetExecutionFlow();
  renderConversationMessages();
  renderConversationList();
}
async function createFreshConversation() {
  const conversation = await createConversationOnServer();
  setCurrentConversationId(conversation.id);
  messages = [];
  resetExecutionFlow();
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
  if (isLoading || isSending) {
    return;
  }

  const content = inputEl.value.trim();
  if (!content) {
    return;
  }

  isSending = true;

  let assistantBubble = null;
  let assistantText = "";
  let traceRequestId = null;

  try {
    await ensureConversationReady();

    const userMessage = { role: "user", content };
    const shouldOfferSql = isSqlIntent(content);

    messages.push(userMessage);
    renderMessage("user", content);
    inputEl.value = "";
    stopRequested = false;
    setLoading(true);
    setExecutionFlowState(
      "running",
      "A acompanhar o pedido atual em tempo real.",
      "A preparar o fluxo do pedido..."
    );

    currentAbortController = new AbortController();

    const response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        messages: messages.map((message) => ({
          role: message.role,
          content: message.content
        }))
      }),
      signal: currentAbortController.signal
    });

    if (!response.ok || !response.body) {
      const rawText = await response.text();
      throw new Error(`POST /api/chat/stream falhou com HTTP ${response.status}: ${rawText}`);
    }

    traceRequestId = response.headers.get("X-Trace-Request-Id");
    trackExecutionFlow(traceRequestId);

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

        if (isToolProgressMessage(data) && !assistantText) {
          continue;
        }

        if (!assistantBubble) {
          assistantBubble = createMessageElement("assistant", "");
        }

        assistantText += data;
        updateMessage(assistantBubble, assistantText);
      }
    }

    assistantText += decoder.decode();
    assistantText = assistantText.trim();

    if (!assistantText) {
      throw new Error("O streaming terminou sem devolver conteÃƒÆ’Ã†â€™Ãƒâ€ Ã¢â‚¬â„¢ÃƒÆ’Ã¢â‚¬Å¡Ãƒâ€šÃ‚Âºdo.");
    }

    messages.push({
      role: "assistant",
      content: assistantText
    });
    await syncConversationOnServer();

    if (shouldOfferSql && assistantBubble) {
      attachSqlButton(assistantBubble, content);
    }
  } catch (error) {
    if (error.name === "AbortError" || stopRequested) {
      assistantText = assistantText.trim();

      if (!assistantBubble) {
        assistantBubble = createMessageElement("assistant", "");
      }

      if (assistantText) {
        updateMessage(assistantBubble, `${assistantText}\n\n[Resposta interrompida]`);
        messages.push({ role: "assistant", content: `${assistantText}\n\n[Resposta interrompida]` });
      } else {
        updateMessage(assistantBubble, "[Resposta interrompida]");
        messages.push({ role: "assistant", content: "[Resposta interrompida]" });
      }

      await syncConversationOnServer();
      statusTextEl.textContent = "Resposta interrompida.";
    } else {
      if (!assistantBubble) {
        assistantBubble = createMessageElement("assistant", "");
      }

      updateMessage(assistantBubble, `Erro: ${error.message}`);
      messages.push({ role: "assistant", content: `Erro: ${error.message}` });
      await syncConversationOnServer();
      statusTextEl.textContent = "Falha ao comunicar com o Ollama.";

      if (!traceRequestId) {
        setExecutionFlowState(
          "error",
          "O fluxo do pedido não pôde ser acompanhado.",
          "Não foi possível carregar o trace deste pedido."
        );
      }
    }
  } finally {
    currentAbortController = null;
    stopRequested = false;
    setLoading(false);
    isSending = false;
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

resetExecutionFlow();
renderConversationMessages();
renderConversationList();
ensureConversationReady().catch((error) => {
  statusTextEl.textContent = `Falha ao carregar memÃƒÆ’Ã†â€™Ãƒâ€šÃ‚Â³ria: ${error.message}`;
});
loadOllamaStatus();





