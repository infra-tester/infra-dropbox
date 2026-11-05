let lastRenderedFilesKey = null;

function setFileStatus(text, tone = "") {
  IDB.setStatus(document.getElementById("file-status"), text, tone);
}

function renderFiles(data) {
  const container = document.getElementById("files");
  const count = document.getElementById("file-count");
  const storage = document.getElementById("file-storage");

  if (!container || !count || !storage) {
    return;
  }

  count.textContent = `${data.files.length} ${
    data.files.length === 1 ? "file" : "files"
  }`;
  storage.textContent = `${IDB.formatBytes(data.used_bytes)} / ${IDB.formatBytes(
    data.max_bytes
  )} used`;

  const renderKey = JSON.stringify([IDB.admin.isUnlocked(), data.files]);

  if (renderKey === lastRenderedFilesKey) {
    return;
  }

  container.replaceChildren();

  if (data.files.length === 0) {
    container.appendChild(IDB.emptyState("No files shared yet."));
    lastRenderedFilesKey = renderKey;
    return;
  }

  data.files.forEach((file) => {
    const card = document.createElement("article");
    const details = document.createElement("div");
    const link = document.createElement("a");
    const meta = document.createElement("span");
    const actions = document.createElement("div");
    const download = document.createElement("a");
    const downloadUrl = `/api/files/${file.id}/download`;

    card.className = "file-card";
    details.className = "file-details";
    link.className = "file-name";
    link.href = downloadUrl;
    link.textContent = file.filename;
    meta.className = "file-meta";
    meta.textContent = `${IDB.formatBytes(file.size)} · ${IDB.formatTimestamp(
      file.created_at
    )}`;
    actions.className = "file-actions";

    download.className = "copy-btn";
    download.href = downloadUrl;
    download.textContent = "Download";
    actions.appendChild(download);

    if (IDB.admin.isUnlocked()) {
      const remove = document.createElement("button");

      remove.type = "button";
      remove.className = "copy-btn danger";
      remove.textContent = "Delete";
      remove.dataset.deleteFileId = file.id;
      actions.appendChild(remove);
    }

    details.append(link, meta);
    card.append(details, actions);
    container.appendChild(card);
  });

  lastRenderedFilesKey = renderKey;
}

async function loadFiles() {
  const container = document.getElementById("files");
  const storage = document.getElementById("file-storage");

  if (!container || !storage) {
    return;
  }

  try {
    const response = await fetch("/api/files");

    if (!response.ok) {
      throw new Error(await IDB.readError(response, "Could not retrieve files."));
    }

    renderFiles(await response.json());
  } catch (error) {
    console.error("File list error:", error);
    lastRenderedFilesKey = null;
    container.replaceChildren(IDB.emptyState("Could not load files. Retrying...", true));
    storage.textContent = "offline";
  }
}

async function uploadFile(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const input = document.getElementById("file-input");
  const button = document.getElementById("file-upload-button");

  if (
    !(form instanceof HTMLFormElement) ||
    !(input instanceof HTMLInputElement)
  ) {
    return;
  }

  if (!input.files || input.files.length === 0) {
    setFileStatus("Choose a file to upload.", "error");
    return;
  }

  const formData = new FormData(form);

  if (button) {
    button.disabled = true;
  }
  setFileStatus("Uploading...");

  try {
    const response = await fetch("/api/files", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(await IDB.readError(response, "Could not upload this file."));
    }

    const result = await response.json();

    form.reset();
    setFileStatus(`${result.file.filename} uploaded.`, "ok");
    IDB.refreshAll();
  } catch (error) {
    console.error("Upload failed:", error);
    setFileStatus(error.message || "Could not reach the server.", "error");
  } finally {
    if (button) {
      button.disabled = false;
    }
  }
}

async function deleteFile(id) {
  if (!IDB.admin.isUnlocked()) {
    return;
  }

  if (!window.confirm("Delete this file? This cannot be undone.")) {
    return;
  }

  try {
    const response = await fetch(`/api/files/${id}/delete`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: IDB.admin.password() }),
    });

    if (!response.ok) {
      IDB.admin.status(
        await IDB.readError(response, "Could not delete the file."),
        "error"
      );
      return;
    }

    IDB.admin.status("File deleted.", "ok");
    loadFiles();
  } catch (error) {
    console.error("File deletion failed:", error);
    IDB.admin.status("Could not reach the server.", "error");
  }
}

const fileUploadForm = document.getElementById("file-upload-form");

if (fileUploadForm) {
  fileUploadForm.addEventListener("submit", uploadFile);
}

if (document.getElementById("files")) {
  loadFiles();
  IDB.onRefresh(loadFiles);
  setInterval(loadFiles, 5000);
}

IDB.onClick("[data-delete-file-id]", (button) => {
  deleteFile(button.dataset.deleteFileId);
});
