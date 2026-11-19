(() => {
  const panel = document.querySelector(".admin-panel");
  const unlockRow = document.getElementById("admin-unlock");
  const unlockButton = document.getElementById("admin-unlock-btn");
  const passwordInput = document.getElementById("admin-password");
  const statusElement = document.getElementById("admin-status");
  const sessionRow = document.getElementById("admin-session");
  const lockButton = document.getElementById("admin-lock");
  const clearButton = document.getElementById("admin-clear");

  const state = { configured: false, unlocked: false };

  function applyState() {
    if (panel) {
      panel.hidden = !state.configured;
    }

    if (unlockRow) {
      unlockRow.hidden = !state.configured || state.unlocked;
    }

    if (sessionRow) {
      sessionRow.hidden = !state.unlocked;
    }

    if (clearButton) {
      clearButton.hidden = !state.unlocked;
    }
  }

  async function sync() {
    try {
      const response = await fetch("/api/admin/status");

      if (!response.ok) {
        return;
      }

      const data = await response.json();
      const wasUnlocked = state.unlocked;

      state.configured = Boolean(data.configured);
      state.unlocked = Boolean(data.unlocked);
      applyState();

      if (wasUnlocked !== state.unlocked) {
        IDB.refreshAll();
      }
    } catch (error) {
      console.error("Admin status check failed:", error);
    }
  }

  async function unlock() {
    if (!passwordInput) {
      return;
    }

    const password = passwordInput.value;

    if (!password) {
      IDB.setStatus(statusElement, "Enter the administrator password.", "error");
      return;
    }

    if (unlockButton) {
      unlockButton.disabled = true;
    }

    try {
      const response = await fetch("/api/admin/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ password }),
      });

      if (!response.ok) {
        IDB.setStatus(
          statusElement,
          await IDB.readError(response, "Could not unlock."),
          "error"
        );
        return;
      }

      state.unlocked = true;
      passwordInput.value = "";
      applyState();
      IDB.setStatus(statusElement, "Unlocked.", "ok");
      IDB.refreshAll();
    } catch (error) {
      console.error("Unlock failed:", error);
      IDB.setStatus(statusElement, "Could not reach the server.", "error");
    } finally {
      if (unlockButton) {
        unlockButton.disabled = false;
      }
    }
  }

  async function lock() {
    try {
      await fetch("/api/admin/logout", { method: "POST" });
    } catch (error) {
      console.error("Lock failed:", error);
    }

    state.unlocked = false;
    applyState();
    IDB.setStatus(statusElement, "Locked.", "ok");
    IDB.refreshAll();
  }

  IDB.admin = {
    isUnlocked: () => state.unlocked,
    status: (text, tone) => IDB.setStatus(statusElement, text, tone),
    sync,
  };

  if (unlockButton) {
    unlockButton.addEventListener("click", unlock);
  }

  if (passwordInput) {
    passwordInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        unlock();
      }
    });
  }

  if (lockButton) {
    lockButton.addEventListener("click", lock);
  }

  applyState();
  sync();
})();
