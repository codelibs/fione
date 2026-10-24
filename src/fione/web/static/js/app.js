// Fione UI behaviour shared by every page: theme toggle, mobile navigation, menus, tabs,
// toasts and HTMX error reporting. No inline handlers: everything is wired up here.
(function () {
  "use strict";

  var root = document.documentElement;
  var body = document.body;
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  // ---- Theme ----------------------------------------------------------------------------
  function currentTheme() {
    var chosen = root.getAttribute("data-theme");
    if (chosen === "light" || chosen === "dark") return chosen;
    return darkQuery.matches ? "dark" : "light";
  }

  function syncThemeToggles() {
    var dark = currentTheme() === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
      button.setAttribute("aria-pressed", dark ? "true" : "false");
    });
  }

  document.querySelectorAll("[data-theme-toggle]").forEach(function (button) {
    button.addEventListener("click", function () {
      var next = currentTheme() === "dark" ? "light" : "dark";
      root.setAttribute("data-theme", next);
      try {
        window.localStorage.setItem("fione-theme", next);
      } catch (e) {
        // Not remembered when storage is unavailable; the page still switches.
      }
      syncThemeToggles();
    });
  });
  darkQuery.addEventListener("change", syncThemeToggles);
  syncThemeToggles();

  // ---- Mobile navigation ----------------------------------------------------------------
  document.querySelectorAll(".nav-toggle").forEach(function (button) {
    var target = document.getElementById(button.getAttribute("aria-controls"));
    if (!target) return;
    function setOpen(open) {
      target.classList.toggle("is-open", open);
      button.setAttribute("aria-expanded", open ? "true" : "false");
    }
    button.addEventListener("click", function () {
      setOpen(!target.classList.contains("is-open"));
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && target.classList.contains("is-open")) {
        setOpen(false);
        button.focus();
      }
    });
  });

  // ---- Menus (<details class="menu">): close on outside click and Escape ---------------
  document.addEventListener("click", function (event) {
    document.querySelectorAll("details.menu[open]").forEach(function (menu) {
      if (!menu.contains(event.target)) menu.removeAttribute("open");
    });
  });
  document.addEventListener("keydown", function (event) {
    if (event.key !== "Escape") return;
    document.querySelectorAll("details.menu[open]").forEach(function (menu) {
      menu.removeAttribute("open");
      menu.querySelector("summary").focus();
    });
  });

  // ---- Tabs (WAI-ARIA tabs, automatic activation, roving tabindex) ---------------------
  function initTabs(list) {
    var tabs = Array.prototype.slice.call(list.querySelectorAll('[role="tab"]'));
    function select(tab, focus) {
      tabs.forEach(function (other) {
        var selected = other === tab;
        other.setAttribute("aria-selected", selected ? "true" : "false");
        other.tabIndex = selected ? 0 : -1;
        var panel = document.getElementById(other.getAttribute("aria-controls"));
        if (panel) panel.hidden = !selected;
      });
      if (focus) tab.focus();
    }
    tabs.forEach(function (tab, index) {
      tab.addEventListener("click", function () {
        select(tab, false);
      });
      tab.addEventListener("keydown", function (event) {
        var next = null;
        if (event.key === "ArrowRight") next = tabs[(index + 1) % tabs.length];
        else if (event.key === "ArrowLeft") next = tabs[(index - 1 + tabs.length) % tabs.length];
        else if (event.key === "Home") next = tabs[0];
        else if (event.key === "End") next = tabs[tabs.length - 1];
        if (next) {
          event.preventDefault();
          select(next, true);
        }
      });
    });
  }
  document.querySelectorAll('[role="tablist"]').forEach(initTabs);

  // ---- Toasts ---------------------------------------------------------------------------
  var toasts = document.getElementById("toasts");
  var TOAST_MS = 6000;

  function dismiss(toast) {
    if (toast.parentNode) toast.parentNode.removeChild(toast);
  }

  function wireToast(toast) {
    if (toast.dataset.wired) return;
    toast.dataset.wired = "1";
    var close = toast.querySelector("[data-toast-close]");
    if (close) {
      close.addEventListener("click", function () {
        dismiss(toast);
      });
    }
    // Errors stay until closed (WCAG 2.2.1); confirmations go away by themselves.
    if (toast.parentNode === toasts && !toast.classList.contains("toast-danger")) {
      window.setTimeout(function () {
        dismiss(toast);
      }, TOAST_MS);
    }
  }

  // Built from the server-rendered <template data-toast-template="success|danger">.
  function showToast(message, kind) {
    var template = document.querySelector('template[data-toast-template="' + kind + '"]');
    if (!template || !toasts) return;
    var toast = template.content.firstElementChild.cloneNode(true);
    toast.querySelector(".toast__text").textContent = message;
    toasts.appendChild(toast);
  }

  if (toasts) {
    new MutationObserver(function (records) {
      records.forEach(function (record) {
        record.addedNodes.forEach(function (node) {
          if (node.nodeType === 1 && node.classList.contains("toast")) wireToast(node);
        });
      });
    }).observe(toasts, { childList: true });
  }
  document.querySelectorAll(".toast").forEach(wireToast);
  document.querySelectorAll("[data-toast-demo]").forEach(function (button) {
    button.addEventListener("click", function () {
      showToast(button.getAttribute("data-toast-demo"), "success");
    });
  });

  // ---- HTMX: report failed requests -----------------------------------------------------
  // The server answers refused UI requests with a short translated text/plain message.
  body.addEventListener("htmx:responseError", function (event) {
    var xhr = event.detail.xhr;
    var type = xhr.getResponseHeader("Content-Type") || "";
    var message = type.indexOf("text/plain") === 0 && xhr.responseText.length < 300
      ? xhr.responseText
      : body.dataset.msgError;
    showToast(message, "danger");
  });
  body.addEventListener("htmx:sendError", function () {
    showToast(body.dataset.msgNetwork, "danger");
  });

  window.fione = { showToast: showToast };
})();
