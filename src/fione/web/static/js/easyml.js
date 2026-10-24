// EasyML wizard behaviour: file drop, busy submit buttons, the custom run time, select all /
// none, copying the serving command, the cancel panel and announcing job progress. Every
// page works without it; this only makes it smoother.
(function () {
  "use strict";

  // ---- Drag and drop onto the file field ----------------------------------------------
  document.querySelectorAll("[data-dropzone]").forEach(function (zone) {
    var input = zone.querySelector('input[type="file"]');
    var label = zone.querySelector("[data-dropzone-file]");
    function showName() {
      var file = input.files && input.files[0];
      label.textContent = file ? file.name : "";
      label.hidden = !file;
      zone.classList.toggle("has-file", !!file);
    }
    ["dragenter", "dragover"].forEach(function (type) {
      zone.addEventListener(type, function (event) {
        event.preventDefault();
        zone.classList.add("is-dragging");
      });
    });
    ["dragleave", "dragend", "drop"].forEach(function (type) {
      zone.addEventListener(type, function () {
        zone.classList.remove("is-dragging");
      });
    });
    zone.addEventListener("drop", function (event) {
      event.preventDefault();
      if (event.dataTransfer && event.dataTransfer.files.length) {
        input.files = event.dataTransfer.files;
        showName();
      }
    });
    input.addEventListener("change", showName);
    showName();
  });

  // ---- Busy buttons: a slow upload, run or cancel is not submitted twice. Delegated, so
  // forms swapped in by HTMX (the run form after a target change) are covered too. -------
  var BUSY = "[data-upload-form], [data-run-form], [data-busy-form]";
  document.addEventListener("submit", function (event) {
    var form = event.target.closest(BUSY);
    if (!form) return;
    if (form.hasAttribute("data-busy")) {
      event.preventDefault(); // already on its way
      return;
    }
    form.setAttribute("data-busy", "");
    var button = form.querySelector('button[type="submit"]');
    // Disabled after this event, so the button's own value is still sent.
    window.setTimeout(function () {
      button.disabled = true;
      button.setAttribute("aria-busy", "true");
    }, 0);
  });
  window.addEventListener("pageshow", function (event) {
    if (!event.persisted) return;
    document.querySelectorAll(BUSY).forEach(function (form) {
      form.removeAttribute("data-busy");
      var button = form.querySelector('button[type="submit"]');
      button.disabled = false;
      button.setAttribute("aria-busy", "false");
    });
  });

  // ---- Custom run time: typing minutes picks the "other" choice --------------------------
  document.addEventListener("input", function (event) {
    if (!event.target.matches("[data-custom-runtime]")) return;
    var radio = document.getElementById("runtime-custom");
    if (radio) radio.checked = true;
  });

  // ---- Select all / none ------------------------------------------------------------------
  function wireChecks(scope) {
    scope.querySelectorAll("[data-check-all], [data-check-none]").forEach(function (button) {
      if (button.dataset.wired) return;
      button.dataset.wired = "1";
      button.hidden = false;
      var all = button.hasAttribute("data-check-all");
      var name = button.getAttribute(all ? "data-check-all" : "data-check-none");
      button.addEventListener("click", function () {
        var fieldset = button.closest("fieldset");
        fieldset.querySelectorAll('input[type="checkbox"][name="' + name + '"]').forEach(
          function (box) {
            box.checked = all;
          }
        );
      });
    });
  }
  wireChecks(document);

  // ---- Copy the serving command -----------------------------------------------------------
  document.querySelectorAll("[data-copy]").forEach(function (button) {
    if (!navigator.clipboard) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      var source = document.getElementById(button.getAttribute("data-copy"));
      navigator.clipboard.writeText(source.textContent).then(function () {
        if (window.fione) window.fione.showToast(button.getAttribute("data-copied"));
      });
    });
  });

  // ---- The cancel panel: opening it moves focus into it (its summary hides); "keep going"
  // closes it ------------------------------------------------------------------------------
  // "toggle" does not bubble: listened for in the capture phase, so panels swapped in by
  // HTMX are covered too.
  document.addEventListener(
    "toggle",
    function (event) {
      var panel = event.target;
      if (!panel.matches || !panel.matches("details[data-confirm-panel]") || !panel.open) return;
      var keep = panel.querySelector("[data-confirm-close]");
      if (keep) keep.focus();
    },
    true
  );
  document.addEventListener("click", function (event) {
    var close = event.target.closest("[data-confirm-close]");
    if (!close) return;
    var panel = close.closest("details");
    panel.removeAttribute("open");
    panel.querySelector("summary").focus();
  });

  // ---- After HTMX swaps: wire new content, announce a new job stage ---------------------
  var announce = document.getElementById("job-announce");
  document.body.addEventListener("htmx:afterSettle", function () {
    wireChecks(document);
    var status = document.getElementById("job-status");
    var stage = status && status.querySelector("[data-announce]");
    if (announce && stage && announce.textContent !== stage.textContent) {
      announce.textContent = stage.textContent;
    }
  });
})();
