  const messagesEl = document.getElementById("messages");
  const statusEl = document.getElementById("status");
  const formEl = document.getElementById("chatForm");
  const inputEl = document.getElementById("messageInput");
  const sendButtonEl = document.getElementById("sendButton");
  const clearButtonEl = document.getElementById("clearButton");

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
    statusEl.textContent = loading ? "A gerar resposta..." : "Pronto.";
  }

  function resetChat() {
    if (isLoading) return;

    messages = [];
    messagesEl.innerHTML = "";
    renderMessage(
      "assistant",
      "Ola! Eu transformo ideias de software em planos tecnicos de MVP. Descreve a tua ideia de projeto e eu organizo a solucao."
    );
    inputEl.focus();
  }

  async function sendMessage() {
    if (isLoading) return;

    const content = inputEl.value.trim();
    if (!content) return;

    messages.push({ role: "user", content });
    renderMessage("user", content);
    inputEl.value = "";
    setLoading(true);

    try {
      const response = await fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({ messages })
      });

      const rawText = await response.text();

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${rawText}`);
      }

      let data;
      try {
        data = JSON.parse(rawText);
      } catch {
        throw new Error(`A API nao devolveu JSON valido. Resposta recebida: ${rawText}`);
      }

      messages.push({ role: "assistant", content: data.reply });
      renderMessage("assistant", data.reply);
    } catch (error) {
      renderMessage("assistant", `Erro: ${error.message}`);
    } finally {
      setLoading(false);
      inputEl.focus();
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

  resetChat();
