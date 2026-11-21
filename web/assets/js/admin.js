(() => {
  const state = { unlocked: false };

  async function sync() {
    try {
      const response = await fetch("/api/admin/status");

      if (!response.ok) {
        return;
      }

      const data = await response.json();
      const wasUnlocked = state.unlocked;

      state.unlocked = Boolean(data.unlocked);
      IDB.setConnection(true);

      if (wasUnlocked !== state.unlocked) {
        IDB.refreshAll();
      }
    } catch (error) {
      console.error("Admin status check failed:", error);
      IDB.setConnection(false);
    }
  }

  IDB.admin = {
    isUnlocked: () => state.unlocked,
    sync,
  };

  sync();
  window.addEventListener("focus", sync);
})();
