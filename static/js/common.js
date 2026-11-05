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
