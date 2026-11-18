(function () {
  var pasteButton = document.getElementById("paste-button");
  var form = document.getElementById("mobile-form");
  var messageInput = document.getElementById("mobile-message");
  var status = document.getElementById("mobile-status");

  if (!pasteButton || !form || !messageInput || !status) {
    return;
  }

  function showMessageInput(message) {
    document.body.className = document.body.className
      .replace(/\bclipboard-ready\b/g, "")
      .replace(/\s+/g, " ")
      .replace(/^\s+|\s+$/g, "");
    messageInput.required = true;
    messageInput.focus();
    status.textContent = message;
  }

  var clipboardSupported =
    window.isSecureContext &&
    navigator.clipboard &&
    typeof navigator.clipboard.readText === "function";

  if (clipboardSupported && !document.body.className.match(/\bshow-message-input\b/)) {
    document.body.className += " clipboard-ready";
  }

  pasteButton.addEventListener("click", function () {
    if (!clipboardSupported) {
      showMessageInput("Paste isn't supported here. Type your message below.");
      return;
    }

    navigator.clipboard.readText().then(
      function (text) {
        if (!text.trim()) {
          showMessageInput("Clipboard is empty. Type your message below.");
          return;
        }

        if (text.length > messageInput.maxLength) {
          showMessageInput("That text is too long. Type a shorter message below.");
          return;
        }

        messageInput.value = text;
        status.textContent = "Text pasted.";
      },
      function (error) {
        console.error("Clipboard read failed:", error);
        showMessageInput("Paste failed. Type your message below.");
      }
    );
  });

  form.addEventListener("submit", function (event) {
    if (!messageInput.value.trim()) {
      event.preventDefault();
      showMessageInput("Paste or type a message before sending.");
    }
  });
})();
