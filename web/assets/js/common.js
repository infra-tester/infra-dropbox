window.IDB = {
  refreshers: [],

  onRefresh(callback) {
    this.refreshers.push(callback);
  },

  refreshAll() {
    this.refreshers.forEach((callback) => callback());
  },
};

IDB.formatTimestamp = function formatTimestamp(iso) {
  const date = new Date(iso);

  if (Number.isNaN(date.getTime())) {
    return iso;
  }

  return date.toLocaleString();
};

IDB.formatBytes = function formatBytes(bytes) {
  if (bytes < 1024) {
    return `${bytes} B`;
  }

  const units = ["KB", "MB", "GB"];
  let value = bytes / 1024;
  let unit = 0;

  while (value >= 1024 && unit < units.length - 1) {
    value /= 1024;
    unit += 1;
  }

  return `${value.toFixed(1)} ${units[unit]}`;
};

IDB.readError = async function readError(response, fallback) {
  try {
    const data = await response.json();

    return data.error || fallback;
  } catch {
    return fallback;
  }
};

IDB.emptyState = function emptyState(text, isError = false) {
  const message = document.createElement("div");

  message.className = isError ? "empty-state is-error" : "empty-state";
  message.textContent = text;

  return message;
};

IDB.setStatus = function setStatus(element, text, tone = "") {
  if (!element) {
    return;
  }

  element.textContent = text;
  element.classList.toggle("is-error", tone === "error");
  element.classList.toggle("is-ok", tone === "ok");
};

IDB.onClick = function onClick(selector, handler) {
  document.addEventListener("click", (event) => {
    if (!(event.target instanceof Element)) {
      return;
    }

    const target = event.target.closest(selector);

    if (target) {
      handler(target, event);
    }
  });
};

IDB.setConnection = function setConnection(online) {
  const badge = document.getElementById("connection-status");

  document.body.classList.toggle("is-offline", !online);

  if (!badge) {
    return;
  }

  badge.hidden = online;
  badge.textContent = online ? "" : "Offline — retrying";
  badge.classList.toggle("is-offline", !online);
};

IDB.copyText = async function copyText(text) {
  // Use the modern Clipboard API when available in a secure context, but
  // fall back if the browser rejects the write (for example, no focus).
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Fall through to the selection-based copy below.
    }
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
};

async function loadLanUrls() {
  const list = document.getElementById("lan-urls");
  const fallback = document.getElementById("lan-urls-fallback");

  if (!list || !fallback) {
    return;
  }

  try {
    const response = await fetch("/api/network");

    if (!response.ok) {
      throw new Error("Network info is unavailable.");
    }

    const data = await response.json();

    if (!data.urls || data.urls.length === 0) {
      fallback.hidden = false;
      return;
    }

    list.replaceChildren();

    data.urls.forEach((url) => {
      const item = document.createElement("li");
      const address = document.createElement("span");
      const copy = document.createElement("button");

      item.className = "lan-url-item";
      address.className = "lan-url";
      address.textContent = url;
      copy.type = "button";
      copy.className = "copy-btn";
      copy.textContent = "Copy";
      copy.dataset.copyUrl = url;

      item.append(address, copy);
      list.appendChild(item);
    });

    list.hidden = false;
  } catch (error) {
    console.error("LAN URL lookup failed:", error);
    fallback.hidden = false;
  }
}

IDB.onClick("[data-copy-url]", async (button) => {
  const status = document.getElementById("lan-urls-status");

  try {
    const copied = await IDB.copyText(button.dataset.copyUrl);

    IDB.setStatus(status, copied ? "Copied." : "Copy failed.", copied ? "ok" : "error");

    if (copied) {
      button.textContent = "Copied!";
      setTimeout(() => {
        button.textContent = "Copy";
      }, 1500);
    }
  } catch (error) {
    console.error("Copy failed:", error);
    IDB.setStatus(status, "Copy failed.", "error");
  }
});

loadLanUrls();
