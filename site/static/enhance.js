/* Enhancements shared by every page. Without this file every page is complete.
 *
 * Plain words (maintainer answer B11): the switch in the page header, shown only when this
 * script runs. On: each term the build marked with data-plain shows that plain wording
 * instead of the Arabic term (the glossary records the wording and its source; the term
 * stays as the title, and the link still opens its glossary entry), and an Arabic term
 * given in brackets after its English (class t-gloss) is hidden by site.css. Off: the page
 * as built. The choice is kept on this device (localStorage) when storage is allowed, and
 * is sent nowhere. Every visible string is in the page (site/i18n/en.json).
 */
(function () {
  "use strict";
  var KEY = "al-marsad.plain-words";
  var button = document.querySelector(".plain-toggle");
  var saved = [];   // [element, its markup as built, its title as built]
  var current = false;

  function remembered() {
    try {
      return window.localStorage.getItem(KEY) === "on";
    } catch (e) {
      return false;   // storage blocked: start from the page as built
    }
  }

  function remember(on) {
    try {
      window.localStorage.setItem(KEY, on ? "on" : "off");
    } catch (e) { /* storage blocked: the choice lasts for this page only */ }
  }

  function apply(on) {
    if (on === current) return;
    current = on;
    document.documentElement.classList.toggle("plain-words", on);
    if (on && !saved.length) {
      var marked = document.querySelectorAll("[data-plain]");
      for (var i = 0; i < marked.length; i++) saved.push([marked[i], marked[i].innerHTML, marked[i].getAttribute("title")]);
    }
    saved.forEach(function (s) {
      var el = s[0];
      if (on) {
        el.setAttribute("title", el.textContent);
        el.textContent = el.getAttribute("data-plain");
      } else {
        el.innerHTML = s[1];
        if (s[2] === null) el.removeAttribute("title");
        else el.setAttribute("title", s[2]);
      }
    });
    if (button) button.setAttribute("aria-pressed", on ? "true" : "false");
  }

  if (button) {
    button.hidden = false;
    button.addEventListener("click", function () {
      var on = button.getAttribute("aria-pressed") !== "true";
      apply(on);
      remember(on);
    });
  }
  if (remembered()) apply(true);
})();
