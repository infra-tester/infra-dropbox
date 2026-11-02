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

    button.textContent = successful ? "COPIED" : "FAILED";
    button.classList.toggle("is-copied", successful);
    button.classList.toggle("is-failed", !successful);
  } catch (error) {
    console.error("Copy failed:", error);
    button.textContent = "FAILED";
    button.classList.remove("is-copied");
    button.classList.add("is-failed");
  }

  setTimeout(() => {
    button.textContent = "COPY";
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

async function loadMessages() {
  try {
    const response = await fetch("/api/messages");

    if (!response.ok) {
      throw new Error("Could not retrieve messages");
    }

    const messages = await response.json();

    const container = document.getElementById("messages");
    const count = document.getElementById("message-count");

    if (!container || !count) {
      return;
    }

    count.textContent = `${messages.length} RECEIVED`;

    container.replaceChildren();

    if (messages.length === 0) {
      const empty = document.createElement("div");

      empty.className = "empty-state";
      empty.textContent = "AWAITING TRANSMISSIONS...";

      container.appendChild(empty);
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
      copy.className = "copy-btn";
      copy.textContent = "COPY";

      actions.appendChild(copy);

      card.append(content, meta, actions);
      container.appendChild(card);
    });
  } catch (error) {
    console.error("Dashboard error:", error);
  }
}

document.addEventListener("click", (event) => {
  const button =
    event.target instanceof Element ? event.target.closest(".copy-btn") : null;

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

document.querySelectorAll("[data-created-at]").forEach((element) => {
  const iso = element.getAttribute("data-created-at");

  element.dateTime = iso;
  element.textContent = formatTimestamp(iso);
});

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
