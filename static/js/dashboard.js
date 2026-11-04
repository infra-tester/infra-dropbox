let adminPassword = "";
let searchQuery = "";
let searchTimer = null;

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

async function handleCopy(button, text) {
  try {
    const successful = await copyText(text);

    button.textContent = successful ? "Copied" : "Failed";
    button.classList.toggle("is-copied", successful);
    button.classList.toggle("is-failed", !successful);
  } catch (error) {
    console.error("Copy failed:", error);
    button.textContent = "Failed";
    button.classList.remove("is-copied");
    button.classList.add("is-failed");
  }

  setTimeout(() => {
    button.textContent = "Copy";
    button.classList.remove("is-copied", "is-failed");
  }, 1500);
}

function formatTimestamp(iso) {
  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) {
    return iso;
  }

  return date.toLocaleString();
}

function messagesEndpoint() {
  return searchQuery
    ? `/api/messages?q=${encodeURIComponent(searchQuery)}`
    : "/api/messages";
}

async function readError(response, fallback) {
  try {
    const data = await response.json();

    return data.error || fallback;
  } catch {
    return fallback;
  }
}

function showListMessage(container, text, isError = false) {
  const message = document.createElement("div");

  message.className = isError ? "empty-state is-error" : "empty-state";
  message.textContent = text;

  container.replaceChildren(message);
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

  container.replaceChildren();

  if (messages.length === 0) {
    showListMessage(
      container,
      searchQuery ? "No messages match this search." : "No messages yet."
    );
    return;
  }

  messages.forEach((message) => {
    const card = document.createElement("article");

    card.className = "message-card";

    // Message content
    const content = document.createElement("div");

    content.className = "message-content";
    content.textContent = message.content;

    // Received time
    const meta = document.createElement("div");

    meta.className = "message-meta";

    const time = document.createElement("time");

    time.className = "message-time";
    time.dateTime = message.created_at;
    time.textContent = formatTimestamp(message.created_at);

    meta.appendChild(time);

    // Message actions
    const actions = document.createElement("div");

    actions.className = "message-actions";

    const copy = document.createElement("button");

    copy.type = "button";
    copy.className = "copy-btn";
    copy.textContent = "Copy";

    actions.appendChild(copy);

    if (adminPassword) {
      const remove = document.createElement("button");

      remove.type = "button";
      remove.className = "copy-btn danger";
      remove.textContent = "Delete";
      remove.dataset.deleteId = message.id;

      actions.appendChild(remove);
    }

    card.append(content, meta, actions);
    container.appendChild(card);
  });
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
      throw new Error(await readError(response, "Could not retrieve messages."));
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

/* Administrator actions */

const adminUnlockRow = document.getElementById("admin-unlock");
const adminUnlockButton = document.getElementById("admin-unlock-btn");
const adminPasswordInput = document.getElementById("admin-password");
const adminStatus = document.getElementById("admin-status");
const adminClearButton = document.getElementById("admin-clear");

function setAdminStatus(text, tone) {
  if (!adminStatus) {
    return;
  }

  adminStatus.textContent = text;
  adminStatus.classList.toggle("is-error", tone === "error");
  adminStatus.classList.toggle("is-ok", tone === "ok");
}

function applyAdminState() {
  const unlocked = Boolean(adminPassword);

  if (adminUnlockRow) {
    adminUnlockRow.hidden = unlocked;
  }

  if (adminClearButton) {
    adminClearButton.hidden = !unlocked;
  }
}

async function unlockAdmin() {
  if (!adminPasswordInput) {
    return;
  }

  const password = adminPasswordInput.value;

  if (!password) {
    setAdminStatus("Enter the administrator password.", "error");
    return;
  }

  if (adminUnlockButton) {
    adminUnlockButton.disabled = true;
  }

  try {
    const response = await fetch("/api/admin/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password }),
    });

    if (!response.ok) {
      setAdminStatus(await readError(response, "Could not unlock."), "error");
      return;
    }

    adminPassword = password;
    adminPasswordInput.value = "";
    applyAdminState();
    setAdminStatus("Unlocked until you reload the page.", "ok");
    loadMessages();
  } catch (error) {
    console.error("Unlock failed:", error);
    setAdminStatus("Could not reach the server.", "error");
  } finally {
    if (adminUnlockButton) {
      adminUnlockButton.disabled = false;
    }
  }
}

async function deleteMessage(id) {
  if (!adminPassword) {
    return;
  }

  if (!window.confirm("Delete this message? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`/api/messages/${id}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: adminPassword }),
    });

    if (!response.ok) {
      setAdminStatus(await readError(response, "Could not delete."), "error");
      return;
    }

    setAdminStatus("Message deleted.", "ok");
    loadMessages();
  } catch (error) {
    console.error("Delete failed:", error);
    setAdminStatus("Could not reach the server.", "error");
  }
}

async function clearMessages() {
  if (!adminPassword) {
    return;
  }

  if (!window.confirm("Delete every message? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch("/api/messages/clear", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: adminPassword }),
    });

    if (!response.ok) {
      setAdminStatus(
        await readError(response, "Could not clear messages."),
        "error"
      );
      return;
    }

    setAdminStatus("All messages deleted.", "ok");
    loadMessages();
  } catch (error) {
    console.error("Clear failed:", error);
    setAdminStatus("Could not reach the server.", "error");
  }
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

  const button = event.target.closest(".copy-btn");

  if (button) {
    const message =
      button.dataset.copyText ??
      button.closest(".message-card")?.querySelector(".message-content")
        ?.textContent;

    if (message !== undefined && message !== null) {
      handleCopy(button, message);
    }
  }
});

const messageInput = document.getElementById("message-input");
const characterCount = document.getElementById("character-count");
const form = document.getElementById("message-form");
const searchInput = document.getElementById("message-search");

if (searchInput) {
  searchInput.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      searchQuery = searchInput.value.trim();
      loadMessages();
    }, 200);
  });
}

if (adminUnlockButton) {
  adminUnlockButton.addEventListener("click", unlockAdmin);
}

if (adminPasswordInput) {
  adminPasswordInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      unlockAdmin();
    }
  });
}

if (adminClearButton) {
  adminClearButton.addEventListener("click", clearMessages);
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

  // Refresh messages every 2 seconds
  setInterval(loadMessages, 2000);
}

// Enter to submit
if (messageInput && form) {
  messageInput.addEventListener("keypress", function (e) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      form.requestSubmit();
    }
  });
}
