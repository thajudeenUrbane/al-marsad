/* Progress on learning paths, kept on this device only (localStorage).
 * The pages are complete without this script: it only adds "done" boxes and a count.
 * A journey's progress is one list of stop keys per journey, so it is shared by every
 * page and every depth (Discover, Study, Research) of that journey: the count is taken
 * over the journey's stops, which each page lists in its article's data-steps and
 * data-total, not over the steps that page happens to hold.
 * It holds no interface text: every word comes from the page (data-template
 * attributes and <template> elements filled from learn/i18n/en.json at build time).
 * If the browser refuses storage (private mode, blocked site data), the script does
 * nothing and the page stays as it is.
 */
(function () {
  "use strict";
  var KEY = "al-marsad.learn.progress.v1";

  function storage() {
    try {
      var s = window.localStorage;
      var probe = KEY + ".probe";
      s.setItem(probe, "1");
      s.removeItem(probe);
      return s;
    } catch (e) {
      return null;
    }
  }

  function load(s) {
    try {
      var v = JSON.parse(s.getItem(KEY) || "{}");
      return v && typeof v === "object" && !Array.isArray(v) ? v : {};
    } catch (e) {
      return {};
    }
  }

  function save(s, all) {
    try {
      s.setItem(KEY, JSON.stringify(all));
      return true;
    } catch (e) {
      return false;
    }
  }

  function fill(template, done, total) {
    return template.replace("{done}", String(done)).replace("{total}", String(total));
  }

  function doneList(all, slug) {
    var list = all[slug];
    return Array.isArray(list) ? list.filter(function (x) { return typeof x === "string"; }) : [];
  }

  function journeyPage(root, s) {
    var slug = root.getAttribute("data-journey");
    var box = root.querySelector("[data-progress]");
    var count = root.querySelector("[data-progress-count]");
    var reset = root.querySelector("[data-progress-reset]");
    var tpl = document.getElementById("learn-step-done");
    var steps = root.querySelectorAll("[data-step]");
    if (!slug || !box || !count || !tpl || !tpl.content || !steps.length) return;
    var keys = (root.getAttribute("data-steps") || "").split(" ").filter(Boolean);
    var total = parseInt(root.getAttribute("data-total") || "", 10);
    if (!(total > 0)) total = keys.length || steps.length;
    var all = load(s);
    var done = doneList(all, slug);

    function refresh() {
      var n = 0;
      for (var i = 0; i < steps.length; i++) {
        var on = done.indexOf(steps[i].getAttribute("data-step")) >= 0;
        if (on) n++;
        steps[i].classList.toggle("is-done", on);
        var cb = steps[i].querySelector("[data-step-check]");
        if (cb) cb.checked = on;
      }
      if (keys.length) n = done.filter(function (k) { return keys.indexOf(k) >= 0; }).length;
      count.textContent = fill(count.getAttribute("data-template") || "", n, total);
    }

    function store() {
      all = load(s);
      all[slug] = done;
      save(s, all);
      refresh();
    }

    for (var i = 0; i < steps.length; i++) {
      (function (step) {
        var key = step.getAttribute("data-step");
        var node = tpl.content.cloneNode(true);
        var cb = node.querySelector("[data-step-check]");
        var title = step.querySelector(".step-title");
        if (!cb) return;
        if (title && title.id) cb.setAttribute("aria-describedby", title.id);
        cb.addEventListener("change", function () {
          var at = done.indexOf(key);
          if (cb.checked && at < 0) done.push(key);
          if (!cb.checked && at >= 0) done.splice(at, 1);
          store();
        });
        if (title && title.nextSibling) step.insertBefore(node, title.nextSibling);
        else step.appendChild(node);
      })(steps[i]);
    }
    if (reset) {
      reset.addEventListener("click", function () {
        done = [];
        store();
      });
    }
    box.hidden = false;
    refresh();
  }

  function indexPage(list, s) {
    var all = load(s);
    var template = list.getAttribute("data-card-template") || "";
    var cards = list.querySelectorAll("[data-journey-card]");
    for (var i = 0; i < cards.length; i++) {
      var slug = cards[i].getAttribute("data-journey-card");
      var keys = (cards[i].getAttribute("data-steps") || "").split(" ").filter(Boolean);
      var out = cards[i].querySelector("[data-card-progress]");
      var n = doneList(all, slug).filter(function (k) { return keys.indexOf(k) >= 0; }).length;
      if (!out || !n) continue;
      out.textContent = fill(template, n, keys.length);
      out.hidden = false;
    }
  }

  function start() {
    var s = storage();
    if (!s) return;
    var journey = document.querySelector("[data-journey]");
    if (journey) journeyPage(journey, s);
    var list = document.querySelector("[data-card-template]");
    if (list) indexPage(list, s);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
