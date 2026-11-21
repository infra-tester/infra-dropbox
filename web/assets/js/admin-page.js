(() => {
  function setStatus(id, text, tone = "") {
    IDB.setStatus(document.getElementById(id), text, tone);
  }

  async function reportError(response, fallback) {
    return IDB.readError(response, fallback);
  }

  const signedOut = document.getElementById("admin-signed-out");
  const signedIn = document.getElementById("admin-signed-in");

  function showSignedIn(unlocked) {
    if (!signedOut || !signedIn) {
      return;
    }

    signedOut.hidden = unlocked;
    signedIn.hidden = !unlocked;
  }

  const signinForm = document.getElementById("admin-signin-form");

  if (signinForm) {
    const signinButton = document.getElementById("admin-signin-btn");
    const passwordInput = document.getElementById("admin-signin-password");

    signinForm.addEventListener("submit", async (event) => {
      event.preventDefault();
      signinButton.disabled = true;

      try {
        const response = await fetch("/api/admin/login", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ password: passwordInput.value }),
        });

        if (!response.ok) {
          setStatus(
            "admin-page-status",
            await reportError(response, "Could not sign in."),
            "error"
          );
          return;
        }

        passwordInput.value = "";
        setStatus("admin-page-status", "");
        showSignedIn(true);
        await IDB.admin.sync();
        loadStats();
        loadSettings();
        IDB.refreshAll();
      } catch (error) {
        console.error("Sign-in failed:", error);
        setStatus("admin-page-status", "Could not reach the server.", "error");
      } finally {
        signinButton.disabled = false;
      }
    });
  }

  const lockButton = document.getElementById("admin-lock-btn");

  if (lockButton) {
    lockButton.addEventListener("click", async () => {
      try {
        const response = await fetch("/api/admin/logout", { method: "POST" });

        if (!response.ok) {
          throw new Error(
            await reportError(response, "Could not lock the admin session.")
          );
        }

        setStatus("danger-status", "");
        showSignedIn(false);
        await IDB.admin.sync();
        IDB.refreshAll();
      } catch (error) {
        console.error("Lock failed:", error);
        setStatus("danger-status", "Could not lock. Please try again.", "error");
      }
    });
  }

  function isVisible() {
    return signedIn && !signedIn.hidden;
  }

  async function loadStats() {
    if (!isVisible() || !document.getElementById("admin-stats")) {
      return;
    }

    try {
      const response = await fetch("/api/admin/stats");

      if (!response.ok) {
        throw new Error(await reportError(response, "Could not load stats."));
      }

      const data = await response.json();

      document.getElementById("stat-messages").textContent = data.messages;
      document.getElementById("stat-files").textContent = data.files;
      document.getElementById("stat-storage").textContent =
        `${IDB.formatBytes(data.used_bytes)} / ${IDB.formatBytes(data.max_bytes)}`;
    } catch (error) {
      console.error("Stats load failed:", error);
      if (isVisible()) {
        document.getElementById("stat-storage").textContent = "unavailable";
      }
    }
  }

  async function loadSettings() {
    if (!isVisible() || !document.getElementById("admin-settings-form")) {
      return;
    }

    const fileInput = document.getElementById("setting-max-file");
    const storageInput = document.getElementById("setting-max-storage");
    const extensionsInput = document.getElementById("setting-extensions");

    try {
      const response = await fetch("/api/admin/settings");

      if (!response.ok) {
        throw new Error(await reportError(response, "Could not load settings."));
      }

      const data = await response.json();

      fileInput.value = data.max_file_bytes / (1024 * 1024);
      storageInput.value = data.max_storage_bytes / (1024 ** 3);
      extensionsInput.value = data.allowed_extensions.join(", ");
    } catch (error) {
      console.error("Settings load failed:", error);
      setStatus("settings-status", error.message, "error");
    }
  }

  const settingsForm = document.getElementById("admin-settings-form");

  if (settingsForm) {
    const fileInput = document.getElementById("setting-max-file");
    const storageInput = document.getElementById("setting-max-storage");
    const extensionsInput = document.getElementById("setting-extensions");
    const saveButton = document.getElementById("settings-save-btn");

    settingsForm.addEventListener("submit", async (event) => {
      event.preventDefault();

      const maxFileMb = Number(fileInput.value);
      const maxStorageGb = Number(storageInput.value);
      const allowedExtensions = extensionsInput.value
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean);

      if (!(maxFileMb > 0) || !(maxStorageGb > 0)) {
        setStatus(
          "settings-status",
          "Enter positive numbers for both limits.",
          "error"
        );
        return;
      }

      saveButton.disabled = true;
      setStatus("settings-status", "Saving...");

      try {
        const response = await fetch("/api/admin/settings", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            max_file_bytes: Math.round(maxFileMb * 1024 * 1024),
            max_storage_bytes: Math.round(maxStorageGb * 1024 ** 3),
            allowed_extensions: allowedExtensions,
          }),
        });

        if (!response.ok) {
          setStatus(
            "settings-status",
            await reportError(response, "Could not save settings."),
            "error"
          );
          return;
        }

        setStatus("settings-status", "Settings saved.", "ok");
        loadStats();
      } catch (error) {
        console.error("Settings save failed:", error);
        setStatus("settings-status", "Could not reach the server.", "error");
      } finally {
        saveButton.disabled = false;
      }
    });
  }

  async function runBulkAction(url, confirmText, successText) {
    if (!window.confirm(confirmText)) {
      return;
    }

    try {
      const response = await fetch(url, { method: "POST" });

      if (!response.ok) {
        setStatus(
          "danger-status",
          await reportError(response, "Could not complete the action."),
          "error"
        );
        return;
      }

      setStatus("danger-status", successText, "ok");
      loadStats();
    } catch (error) {
      console.error("Bulk action failed:", error);
      setStatus("danger-status", "Could not reach the server.", "error");
    }
  }

  const clearMessagesButton = document.getElementById("admin-clear-messages");

  if (clearMessagesButton) {
    clearMessagesButton.addEventListener("click", () => {
      runBulkAction(
        "/api/messages/clear",
        "Delete every message? This cannot be undone.",
        "All messages deleted."
      );
    });
  }

  const clearFilesButton = document.getElementById("admin-clear-files");

  if (clearFilesButton) {
    clearFilesButton.addEventListener("click", () => {
      runBulkAction(
        "/api/files/clear",
        "Delete every shared file? This cannot be undone.",
        "All files deleted."
      );
    });
  }

  IDB.onRefresh(() => showSignedIn(IDB.admin.isUnlocked()));

  loadStats();
  loadSettings();
})();
