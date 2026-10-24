// Sign-in and first-admin forms: post the fields as JSON to the API (data-endpoint), then go
// to data-next, which the server has already checked is a path on this site. Errors are
// shown from the form's data-error-<code> messages, never from the server's text.
(function () {
  "use strict";

  document.querySelectorAll("form[data-json-form]").forEach(function (form) {
    var alertBox = form.parentNode.querySelector("[data-form-error]");
    var button = form.querySelector('button[type="submit"]');
    button.disabled = false; // rendered disabled: without this script the form must not submit

    function message(code) {
      return form.getAttribute("data-error-" + code) || form.getAttribute("data-error-default");
    }

    function showError(text) {
      alertBox.textContent = text;
      alertBox.hidden = false;
    }

    function setBusy(busy) {
      if (busy) form.setAttribute("data-busy", "");
      else form.removeAttribute("data-busy");
      button.disabled = busy;
      button.setAttribute("aria-busy", busy ? "true" : "false");
    }

    // Back/forward cache: a page left mid-submit comes back with a usable button.
    window.addEventListener("pageshow", function (event) {
      if (event.persisted) setBusy(false);
    });

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      alertBox.hidden = true;
      var confirm = form.querySelector("[data-confirm]");
      if (confirm && confirm.value !== form.elements[confirm.getAttribute("data-confirm")].value) {
        showError(message("mismatch"));
        confirm.focus();
        return;
      }
      var data = {};
      Array.prototype.forEach.call(form.elements, function (field) {
        if (field.name && !field.hasAttribute("data-confirm")) data[field.name] = field.value;
      });
      setBusy(true);
      fetch(form.getAttribute("data-endpoint"), {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", Accept: "application/json" },
        body: JSON.stringify(data),
      }).then(
        function (response) {
          if (response.ok) {
            window.location.assign(form.getAttribute("data-next") || "/");
            return;
          }
          return response.json().catch(function () {
            return {};
          }).then(function (body) {
            setBusy(false);
            showError(message(body.code || "default"));
          });
        },
        function () {
          setBusy(false);
          showError(message("network"));
        }
      );
    });
  });
})();
