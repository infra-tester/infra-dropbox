let searchQuery = "";
let searchTimer = null;
let lastRenderedMessagesKey = null;

const messageInput = document.getElementById("message-input");
const characterCount = document.getElementById("character-count");
const searchInput = document.getElementById("message-search");
const clearButton = document.getElementById("admin-clear");

function messagesEndpoint() {
  return searchQuery
    ? `/api/messages?q=${encodeURIComponent(searchQuery)}`
    : "/api/messages";
}

async function copyText(text) {
  // Use the modern Clipboard API when available in a secure context.
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return true;
  }

  // Fallback for browsers accessing the dashboard over local HTTP.
  const textarea = document.createElement("textarea");

  textarea.value = text;
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";

  document.body.appendChild(textarea);
  textarea.select();

  const successful = document.execCommand("copy");

  textarea.remove();

  return successful;
}

const copyFeedbackTimers = new WeakMap();

async function handleCopy(card, text, line = null) {
  const feedback = card.querySelector(".message-copy-feedback");

  if (!feedback) {
    return;
  }

  clearTimeout(copyFeedbackTimers.get(feedback));
  card.querySelector(".message-line.is-copied")?.classList.remove("is-copied");
  feedback.textContent = "Copying...";
  feedback.classList.remove("is-failed");
  feedback.classList.add("is-visible");
  line?.classList.add("is-copied");

  try {
    const successful = await copyText(text);

    feedback.textContent = successful
      ? line
        ? "Line copied"
        : "Message copied"
      : "Copy failed";
    feedback.classList.toggle("is-failed", !successful);
    line?.classList.toggle("is-copied", successful);

    if (!successful) {
      console.error("Copy failed: clipboard operation was unsuccessful.");
    }
  } catch (error) {
    console.error("Copy failed:", error);
    feedback.textContent = "Copy failed";
    feedback.classList.add("is-failed");
    line?.classList.remove("is-copied");
  }

  feedback.classList.add("is-visible");
  clearTimeout(copyFeedbackTimers.get(feedback));

  copyFeedbackTimers.set(
    feedback,
    setTimeout(() => {
      feedback.classList.remove("is-visible", "is-failed");
      line?.classList.remove("is-copied");
    }, 1500)
  );
}

function showListMessage(container, text, isError = false) {
  lastRenderedMessagesKey = null;
  container.replaceChildren(IDB.emptyState(text, isError));
}

function renderMessages(messages) {
  const container = document.getElementById("messages");
  const count = document.getElementById("message-count");

  if (!container || !count) {
    return;
  }

  const noun = searchQuery
    ? messages.length === 1
      ? "match"
      : "matches"
    : messages.length === 1
      ? "message"
      : "messages";
  const label = `${messages.length} ${noun}`;

  if (count.textContent !== label) {
    count.textContent = label;
  }

  const renderKey = JSON.stringify([
    searchQuery,
    IDB.admin.isUnlocked(),
    messages,
  ]);

  if (renderKey === lastRenderedMessagesKey) {
    return;
  }

  container.replaceChildren();

  if (messages.length === 0) {
    showListMessage(
      container,
      searchQuery ? "No messages match this search." : "No messages yet."
    );
    lastRenderedMessagesKey = renderKey;
    return;
  }

  messages.forEach((message) => {
    const card = document.createElement("article");

    card.className = "message-card";

    const content = document.createElement("div");

    content.className = "message-content";

    message.content.split(/\r\n|\n|\r/).forEach((text, index) => {
      const line = document.createElement("button");

      line.type = "button";
      line.className = "message-line";
      line.textContent = text;
      line.dataset.copyLine = "";
      line.setAttribute("aria-label", `Copy message line ${index + 1}`);
      content.appendChild(line);
    });

    card.dataset.copyText = message.content;

    const meta = document.createElement("div");

    meta.className = "message-meta";

    const time = document.createElement("time");

    time.className = "message-time";
    time.dateTime = message.created_at;
    time.textContent = IDB.formatTimestamp(message.created_at);

    meta.appendChild(time);

    const actions = document.createElement("div");

    actions.className = "message-actions";

    if (IDB.admin.isUnlocked()) {
      const remove = document.createElement("button");

      remove.type = "button";
      remove.className = "copy-btn danger";
      remove.textContent = "Delete";
      remove.dataset.deleteId = message.id;

      actions.appendChild(remove);
    }

    const feedback = document.createElement("span");

    feedback.className = "message-copy-feedback";
    feedback.setAttribute("role", "status");
    feedback.setAttribute("aria-live", "polite");

    card.append(content, meta);

    if (IDB.admin.isUnlocked()) {
      card.appendChild(actions);
    }

    card.appendChild(feedback);
    container.appendChild(card);
  });

  lastRenderedMessagesKey = renderKey;
}

async function loadMessages() {
  const container = document.getElementById("messages");
  const count = document.getElementById("message-count");

  if (!container || !count) {
    return;
  }

  try {
    const response = await fetch(messagesEndpoint());

    if (!response.ok) {
      throw new Error(await IDB.readError(response, "Could not retrieve messages."));
    }

    renderMessages(await response.json());
  } catch (error) {
    console.error("Dashboard error:", error);
    showListMessage(container, "Could not load messages. Retrying...", true);

    if (count.textContent !== "offline") {
      count.textContent = "offline";
    }
  }
}

async function deleteMessage(id) {
  if (!IDB.admin.isUnlocked()) {
    return;
  }

  if (!window.confirm("Delete this message? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`/api/messages/${id}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: IDB.admin.password() }),
    });

    if (!response.ok) {
      IDB.admin.status(await IDB.readError(response, "Could not delete."), "error");
      return;
    }

    IDB.admin.status("Message deleted.", "ok");
    loadMessages();
  } catch (error) {
    console.error("Delete failed:", error);
    IDB.admin.status("Could not reach the server.", "error");
  }
}

async function clearMessages() {
  if (!IDB.admin.isUnlocked()) {
    return;
  }

  if (!window.confirm("Delete every message? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch("/api/messages/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: IDB.admin.password() }),
    });

    if (!response.ok) {
      IDB.admin.status(
        await IDB.readError(response, "Could not clear messages."),
        "error"
      );
      return;
    }

    IDB.admin.status("All messages deleted.", "ok");
    loadMessages();
  } catch (error) {
    console.error("Clear failed:", error);
    IDB.admin.status("Could not reach the server.", "error");
  }
}

if (searchInput) {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = searchInput.value.trim();
      loadMessages();
    }, 200);
  });
}

if (clearButton) {
  clearButton.addEventListener("click", clearMessages);
}

if (messageInput && characterCount) {
  const updateCharacterCount = () => {
    characterCount.textContent = 200 - messageInput.value.length;
  };

  messageInput.addEventListener("input", updateCharacterCount);
  updateCharacterCount();
}

if (document.getElementById("messages")) {
  loadMessages();
  IDB.onRefresh(loadMessages);
  setInterval(loadMessages, 2000);
}

document.addEventListener("click", (event) => {
  if (!(event.target instanceof Element)) {
    return;
  }

  const deleteButton = event.target.closest("[data-delete-id]");

  if (deleteButton) {
    deleteMessage(deleteButton.dataset.deleteId);
    return;
  }

  const line = event.target.closest("[data-copy-line]");

  if (line) {
    const card = line.closest(".message-card");

    if (card) {
      handleCopy(card, line.textContent ?? "", line);
    }
    return;
  }

  const card = event.target.closest(".message-card");

  if (card) {
    handleCopy(card, card.dataset.copyText ?? "");
  }
});
