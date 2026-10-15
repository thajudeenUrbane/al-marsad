/* Review pages (slice 3b): keep the pages a reviewer has opened, so they open again
 * without a connection. Network first, so a rebuilt page is used whenever there is a
 * connection; the copy kept here is used only when there is none. Same-site GET only. */
var CACHE = "marsad-review-1";
self.addEventListener("install", function () { self.skipWaiting(); });
self.addEventListener("activate", function (e) { e.waitUntil(self.clients.claim()); });
self.addEventListener("fetch", function (e) {
  var req = e.request;
  if (req.method !== "GET" || new URL(req.url).origin !== self.location.origin) return;
  e.respondWith(fetch(req).then(function (res) {
    if (res.ok) {
      var copy = res.clone();
      caches.open(CACHE).then(function (c) { return c.put(req, copy); });
    }
    return res;
  }, function () {
    return caches.match(req, { ignoreSearch: true }).then(function (hit) { return hit || Response.error(); });
  }));
});
