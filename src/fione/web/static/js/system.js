// The system page: says in the live region when the polled status line changes (the job
// runner, the queue), rather than reading the whole card every 10 s.
(function () {
  "use strict";
  var announce = document.getElementById("system-announce");
  function summary() {
    var el = document.querySelector("#system-status [data-announce]");
    return el ? el.textContent : null;
  }
  var last = summary();
  document.body.addEventListener("htmx:afterSettle", function () {
    var now = summary();
    if (announce && now !== null && now !== last) announce.textContent = now;
    last = now;
  });
})();
