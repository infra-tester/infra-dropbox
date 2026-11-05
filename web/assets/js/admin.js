(() => {
  const unlockRow = document.getElementById("admin-unlock");
  const unlockButton = document.getElementById("admin-unlock-btn");
  const passwordInput = document.getElementById("admin-password");
  const statusElement = document.getElementById("admin-status");
  const clearButton = document.getElementById("admin-clear");

  const state = { password: "" };

  function applyState() {
    const unlocked = Boolean(state.password);

    if (unlockRow) {
      unlockRow.hidden = unlocked;
    }

    if (clearButton) {
      clearButton.hidden = !unlocked;
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
      const response = await fetch("/api/admin/verify", {
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

      state.password = password;
      passwordInput.value = "";
      applyState();
      IDB.setStatus(statusElement, "Unlocked until you reload the page.", "ok");
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

  IDB.admin = {
    isUnlocked: () => Boolean(state.password),
    password: () => state.password,
    status: (text, tone) => IDB.setStatus(statusElement, text, tone),
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

  applyState();
})();
