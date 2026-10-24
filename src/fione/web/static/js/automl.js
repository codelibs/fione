// AutoML screens: metric choices that follow the prediction type in the training form, and
// the polled job list (paused while a confirm panel in it is open, changes announced).
(function () {
  "use strict";

  // ---- Training form: show only the metrics of the chosen (or detected) task ---------
  function syncMetrics(form) {
    var select = form.querySelector("[data-task-select]");
    if (!select) return;
    var task = select.value === "auto" ? form.getAttribute("data-detected-task") : select.value;
    form.querySelectorAll("[data-metric-select]").forEach(function (metric) {
      Array.prototype.forEach.call(metric.options, function (option) {
        var other = option.hasAttribute("data-task") && option.getAttribute("data-task") !== task;
        option.hidden = other;
        option.disabled = other;
        if (other && option.selected) metric.value = "auto";
      });
    });
  }
  function wireForms() {
    document.querySelectorAll("form[data-detected-task]").forEach(function (form) {
      if (form.dataset.wired) return;
      form.dataset.wired = "1";
      var select = form.querySelector("[data-task-select]");
      if (select) select.addEventListener("change", function () { syncMetrics(form); });
      syncMetrics(form);
    });
  }
  wireForms();

  // ---- Job list: no refresh while a confirm panel is open (it would close it) -----------
  document.body.addEventListener("htmx:beforeRequest", function (event) {
    var elt = event.detail && event.detail.elt;
    if (elt && elt.id === "job-list" && elt.querySelector("details[open]")) {
      event.preventDefault();
    }
  });

  var announce = document.getElementById("jobs-announce");
  var last = null;
  function summary() {
    var el = document.querySelector("#job-list [data-announce]");
    return el ? el.textContent : null;
  }
  last = summary();
  document.body.addEventListener("htmx:afterSettle", function () {
    wireForms();
    var now = summary();
    if (announce && now !== null && now !== last) announce.textContent = now;
    last = now;
  });
})();
