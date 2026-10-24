// Runs before the stylesheets apply: marks JS as available and restores the chosen theme,
// so the page never flashes in the wrong one. Without a stored choice the system's applies.
(function () {
  var root = document.documentElement;
  root.classList.add("js");
  try {
    var theme = window.localStorage.getItem("fione-theme");
    if (theme === "light" || theme === "dark") root.setAttribute("data-theme", theme);
  } catch (e) {
    // Storage may be unavailable (private mode, blocked site data): use the system theme.
  }
})();
