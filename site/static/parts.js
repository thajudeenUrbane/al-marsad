/* One long page in parts (maintainer H3, slice 11b): a progressive enhancement.
 *
 * A record with many claims is built as part 1 at its own address and parts 2, 3 ... as
 * pages of their own (part-2/, part-3/ ...), linked from each other: without this file every
 * part is a complete page. With it, when the reader nears the end of a part, the next part's
 * claims are fetched (the page the nav's data-next names, on the same site) and added below,
 * until the last. A button does the same for anyone who prefers to ask. Every visible string
 * is in the page (data-load, from site/i18n).
 */
(function () {
  "use strict";
  var navs = document.querySelectorAll("nav.parts[data-next]");
  if (!navs.length || !window.fetch || !window.DOMParser) return;
  var last = navs[navs.length - 1];
  var body = last.previousElementSibling && last.previousElementSibling.classList.contains("part-body")
    ? last.previousElementSibling : document.querySelector(".part-body:last-of-type");
  if (!body) return;
  var next = new URL(last.getAttribute("data-next"), location.href).href;
  var busy = false, done = false, observer = null;
  var button = document.createElement("button");
  button.type = "button";
  button.className = "parts-load";
  button.textContent = last.getAttribute("data-load");
  last.parentNode.insertBefore(button, last);

  function more() {
    if (busy || done) return;
    busy = true;
    button.disabled = true;
    fetch(next).then(function (r) {
      if (!r.ok) throw new Error(String(r.status));
      return r.text();
    }).then(function (text) {
      var doc = new DOMParser().parseFromString(text, "text/html");
      var part = doc.querySelector(".part-body");
      var nav = doc.querySelector("nav.parts");
      if (!part) throw new Error("no part");
      // links in the fetched part are relative to its own address
      part.querySelectorAll("a[href]").forEach(function (a) {
        a.setAttribute("href", new URL(a.getAttribute("href"), next).href);
      });
      var holder = document.createElement("div");
      holder.className = "part-body part-added";
      holder.setAttribute("data-part", part.getAttribute("data-part") || "");
      while (part.firstChild) holder.appendChild(part.firstChild);
      body.parentNode.insertBefore(holder, button);
      body = holder;
      var to = nav && nav.getAttribute("data-next");
      if (to) {
        next = new URL(to, next).href;
        button.textContent = nav.getAttribute("data-load");
        button.disabled = false;
      } else {
        done = true;
        button.hidden = true;
        if (observer) observer.disconnect();
      }
      busy = false;
    }).catch(function () {
      busy = false;
      button.disabled = false;   // the links below still lead to every part
    });
  }

  button.addEventListener("click", more);
  if ("IntersectionObserver" in window) {
    observer = new IntersectionObserver(function (entries) {
      if (entries.some(function (en) { return en.isIntersecting; })) more();
    }, { rootMargin: "600px 0px" });
    observer.observe(button);
  }
})();
